# Copyright (c) 2001-2016 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

"""
 ****************************************************************************
  Description:       Catches SNMP traps, determines PDU or Switch and
                    notifies the appropriate trap msg handler.
 ****************************************************************************
"""
import json

from framework.base.module_thread import SensorThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger

# Modules that receive messages from this module
from framework.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from message_handlers.logging_msg_handler import LoggingMsgHandler

from json_msgs.messages.sensors.snmp_trap import SNMPtrapMsg

from pysnmp.smi import builder, view

from pysnmp.carrier.asynsock.dispatch import AsynsockDispatcher
from pysnmp.carrier.asynsock.dgram import udp, udp6
from pyasn1.codec.ber import decoder
from pysnmp.proto import api


from zope.interface import implementer
from sensors.INode_data import INodeData
from framework.utils.conf_utils import *

@implementer(INodeData)
class SNMPtraps(SensorThread, InternalMsgQ):

    SENSOR_NAME       = "SNMPtraps"
    PRIORITY          = 1

    # Section and keys in configuration file
    SNMPTRAPS         = SENSOR_NAME.upper()
    ENABLED_TRAPS     = 'enabled_traps'
    BIND_IP           = 'bind_ip'
    BIND_PORT         = 'bind_port'
    ENABLED_MIBS      = 'enabled_MIBS'


    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return SNMPtraps.SENSOR_NAME

    def __init__(self):
        super(SNMPtraps, self).__init__(self.SENSOR_NAME,
                                         self.PRIORITY)
        self._latest_trap = {}

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(SNMPtraps, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(SNMPtraps, self).initialize_msgQ(msgQlist)

        self._set_debug(True)
        self._set_debug_persist(True)

        self._get_config()

        return True

    def read_data(self):
        """Return the most recent trap information"""
        return self._latest_trap

    def run(self):
        """Run the sensor on its own thread"""

        # Check for debug mode being activated/deactivated
        self._read_my_msgQ_noWait()

        try:
            self._log_debug("Start processing")

            # Create MIB loader to lookup oids sent in traps
            self._mib_builder()

            # Create an asynchronous dispatcher and register a callback method to handle incoming traps
            transportDispatcher = AsynsockDispatcher()
            transportDispatcher.registerRecvCbFun(self._trap_catcher)

            # UDP/IPv4
            transportDispatcher.registerTransport(
                udp.domainName, udp.UdpSocketTransport().openServerMode((self._bind_ip, self._bind_port)))

            # UDP/IPv6
            transportDispatcher.registerTransport(
                udp6.domainName, udp6.Udp6SocketTransport().openServerMode(('::1', self._bind_port)))

            transportDispatcher.jobStarted(1)

            try:
                # Dispatcher will never finish as job #1 never reaches zero
                transportDispatcher.runDispatcher()
            except Exception as ae:
                self._log_debug("Exception: %r" % ae)
                transportDispatcher.closeDispatcher()

            self._log_debug("Finished processing, restarting SNMP listener")

            # Reset debug mode if persistence is not enabled
            self._disable_debug_if_persist_false()

            # Schedule the next time to run thread
            self._scheduler.enter(10, self._priority, self.run, ())

        # Could not bind to IP:port, log it and exit out module
        except Exception as ae:
            self._log_debug("Unable to process SNMP traps from this node, closing module.")
            self._log_debug(f"SNMP Traps sensor attempted to bind to {self._bind_ip}:{self._bind_port}")

    def _mib_builder(self):
        """Loads the MIB files and creates dicts with hierarchical structure"""

        # Create MIB loader/builder
        mibBuilder = builder.MibBuilder()

        self._log_debug('Reading MIB sources...')
        mibSources = mibBuilder.getMibSources() + (
            builder.DirMibSource('/etc/sspl-ll/templates/snmp'),)
        mibBuilder.setMibSources(*mibSources)

        self._log_debug("MIB sources: %s" % str(mibBuilder.getMibSources()))
        for module in self._enabled_MIBS:
            mibBuilder.loadModules(module)
        self._mibView = view.MibViewController(mibBuilder)

    def _mib_oid_value(self, oid, val):
        """Look up the trap name using the OID in the MIB"""
        ret_val  = "N/A"
        nodeDesc = "N/A"
        try:
            # Retrieve information in MIB using the OID
            modName, nodeDesc, suffix = self._mibView.getNodeLocation(oid)
            ret_val = val.getComponent().getComponent().getComponent().prettyPrint()
            self._log_debug(f'module: {modName}, {nodeDesc}: {ret_val}, oid: {oid.prettyPrint()}')

            # Lookup the trap name from the SNMP Modules MIB
            if nodeDesc == "snmpModules":
                # Convert the dot notated str oid to a tuple of ints for getNodeName API call
                trap_oid = val.getComponent().getComponent().getComponent().prettyPrint()
                tmp_oid = trap_oid.split(".")
                tuple_oid = tuple([int(x) for x in tmp_oid])

                oid, label, suffix = self._mibView.getNodeName(tuple_oid)
                self._trap_name = str(label[-1])
                self._log_debug(f'Trap Notification: {self._trap_name}')
        except Exception as ae:
            self._log_debug("_mib_oid_value: %r" % ae)
        return (nodeDesc, ret_val)

    def _trap_catcher(self, transportDispatcher, transportDomain, transportAddress, wholeMsg):
        """Callback method when a SNMP trap arrives"""
        json_data = {}
        self._trap_name = ""

        while wholeMsg:
            msgVer = int(api.decodeMessageVersion(wholeMsg))
            if msgVer in api.protoModules:
                pMod = api.protoModules[msgVer]
            else:
                self._log_debug(f'Unsupported SNMP version {msgVer}')
                return

            reqMsg, wholeMsg = decoder.decode(
                wholeMsg, asn1Spec=pMod.Message(),)
            self._log_debug(f'Notification message from {transportDomain}:{transportAddress}: ')

            reqPDU = pMod.apiMessage.getPDU(reqMsg)
            if reqPDU.isSameTypeWith(pMod.TrapPDU()):
                if msgVer == api.protoVersion1:
                    self._log_debug(f'Enterprise: {pMod.apiTrapPDU.getEnterprise(reqPDU).prettyPrint()}')

                    self._log_debug(f'Agent Address: {pMod.apiTrapPDU.getAgentAddr(reqPDU).prettyPrint()}')

                    self._log_debug(f'Generic Trap: {pMod.apiTrapPDU.getGenericTrap(reqPDU).prettyPrint()}')

                    self._log_debug(f'Specific Trap: {pMod.apiTrapPDU.getSpecificTrap(reqPDU).prettyPrint()}')

                    self._log_debug(f'Uptime: {pMod.apiTrapPDU.getTimeStamp(reqPDU).prettyPrint()}')

                    varBinds = pMod.apiTrapPDU.getVarBindList(reqPDU)
                else:
                    varBinds = pMod.apiPDU.getVarBindList(reqPDU)

                for oid, val in varBinds:
                    nodeDesc, ret_val = self._mib_oid_value(oid, val)

                    # Build up JSON data to be logged in IEM and sent to Halon
                    if nodeDesc != "N/A" and ret_val != "N/A":
                        json_data[nodeDesc] = ret_val

        self._log_debug(f"trap_name: {self._trap_name}")
        self._log_debug(f"enabled_traps: {self._enabled_traps}")

        # Apply filter unless there is an asterisk in the list
        if '*' in self._enabled_traps or \
            self._trap_name in self._enabled_traps:

            # Log IEM
            self._log_iem(json_data)

            # Transmit to Halon
            self._transmit_json_msg(json_data)

    def _log_iem(self, json_data):
        """Create IEM and send to logging msg handler"""
        log_msg = f"IEC: 020004001: SNMP Trap Received, {self._trap_name}"
        internal_json_msg = json.dumps(
                    {"actuator_request_type" : {
                        "logging": {
                            "log_level": "LOG_WARNING",
                            "log_type": "IEM",
                            "log_msg": f"{log_msg}:{json.dumps(json_data, sort_keys=True)}"
                            }
                        }
                     })

        # Send the event to logging msg handler to send IEM message to journald
        self._write_internal_msgQ(LoggingMsgHandler.name(), internal_json_msg)

    def _transmit_json_msg(self, json_data):
        """Transmit message to halon by passing it to egress msg handler"""
        json_data["trapName"] = self._trap_name
        json_msg = SNMPtrapMsg(json_data).getJson()
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

    def _get_config(self):
        """Retrieves the information in /etc/sspl.conf"""
        self._enabled_traps = Conf.get(SSPL_CONF, f"{self.SNMPTRAPS}>{self.ENABLED_TRAPS}")
        self._enabled_MIBS  = Conf.get(SSPL_CONF, f"{self.SNMPTRAPS}>{self.ENABLED_MIBS}")

        self._bind_ip = Conf.get(SSPL_CONF, f"{self.SNMPTRAPS}>{self.BIND_IP}",
                                                        'service')
        self._bind_port = int(Conf.get(SSPL_CONF, f"{self.SNMPTRAPS}>{self.BIND_PORT}",
                                                        1620))

        logger.info("          Listening on %s:%s" % (self._bind_ip, self._bind_port))
        logger.info("          Enabled traps: %s" % str(self._enabled_traps))
        logger.info("          Enabled MIBS: %s" % str(self._enabled_MIBS))

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(SNMPtraps, self).shutdown()
