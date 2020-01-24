"""
 ****************************************************************************
 Filename:          SNMP_Traps.py
 Description:       Catches SNMP traps, determines PDU or Switch and
                    notifies the appropriate trap msg handler.
 Creation Date:     3/08/2016
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import json

from framework.base.module_thread import ScheduledModuleThread
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

from zope.interface import implements
from sensors.INode_data import INodeData


class SNMPtraps(ScheduledModuleThread, InternalMsgQ):

    implements(INodeData)

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
            self._log_debug("SNMP Traps sensor attempted to bind to %s:%s" %
                            (self._bind_ip, self._bind_port))

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
            self._log_debug('module: %s, %s: %s, oid: %s' %
                            (modName, nodeDesc, ret_val, oid.prettyPrint()))

            # Lookup the trap name from the SNMP Modules MIB
            if nodeDesc == "snmpModules":
                # Convert the dot notated str oid to a tuple of ints for getNodeName API call
                trap_oid = val.getComponent().getComponent().getComponent().prettyPrint()
                tmp_oid = trap_oid.split(".")
                tuple_oid = tuple([int(x) for x in tmp_oid])

                oid, label, suffix = self._mibView.getNodeName(tuple_oid)
                self._trap_name = str(label[-1])
                self._log_debug('Trap Notification: %s' % self._trap_name)
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
                self._log_debug('Unsupported SNMP version %s' % msgVer)
                return

            reqMsg, wholeMsg = decoder.decode(
                wholeMsg, asn1Spec=pMod.Message(),)
            self._log_debug('Notification message from %s:%s: ' %
                                (transportDomain, transportAddress))

            reqPDU = pMod.apiMessage.getPDU(reqMsg)
            if reqPDU.isSameTypeWith(pMod.TrapPDU()):
                if msgVer == api.protoVersion1:
                    self._log_debug('Enterprise: %s' %
                            (pMod.apiTrapPDU.getEnterprise(reqPDU).prettyPrint()))

                    self._log_debug('Agent Address: %s' %
                            (pMod.apiTrapPDU.getAgentAddr(reqPDU).prettyPrint()))

                    self._log_debug('Generic Trap: %s' %
                            (pMod.apiTrapPDU.getGenericTrap(reqPDU).prettyPrint()))

                    self._log_debug('Specific Trap: %s' %
                            (pMod.apiTrapPDU.getSpecificTrap(reqPDU).prettyPrint()))

                    self._log_debug('Uptime: %s' %
                            (pMod.apiTrapPDU.getTimeStamp(reqPDU).prettyPrint()))

                    varBinds = pMod.apiTrapPDU.getVarBindList(reqPDU)
                else:
                    varBinds = pMod.apiPDU.getVarBindList(reqPDU)

                for oid, val in varBinds:
                    nodeDesc, ret_val = self._mib_oid_value(oid, val)

                    # Build up JSON data to be logged in IEM and sent to Halon
                    if nodeDesc != "N/A" and ret_val != "N/A":
                        json_data[nodeDesc] = ret_val

        self._log_debug("trap_name: %s" % self._trap_name)
        self._log_debug("enabled_traps: %s " % self._enabled_traps)

        # Apply filter unless there is an asterisk in the list
        if '*' in self._enabled_traps or \
            self._trap_name in self._enabled_traps:

            # Log IEM
            self._log_iem(json_data)

            # Transmit to Halon
            self._transmit_json_msg(json_data)

    def _log_iem(self, json_data):
        """Create IEM and send to logging msg handler"""
        log_msg = "IEC: 020004001: SNMP Trap Received, {}".format(self._trap_name)
        internal_json_msg = json.dumps(
                    {"actuator_request_type" : {
                        "logging": {
                            "log_level": "LOG_WARNING",
                            "log_type": "IEM",
                            "log_msg": "{}:{}".format(log_msg, json.dumps(json_data, sort_keys=True))
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
        self._enabled_traps = self._conf_reader._get_value_list(self.SNMPTRAPS,
                                                        self.ENABLED_TRAPS)
        self._enabled_MIBS  = self._conf_reader._get_value_list(self.SNMPTRAPS,
                                                        self.ENABLED_MIBS)

        self._bind_ip = self._conf_reader._get_value_with_default(self.SNMPTRAPS,
                                                        self.BIND_IP,
                                                        'service')
        self._bind_port = int(self._conf_reader._get_value_with_default(self.SNMPTRAPS,
                                                        self.BIND_PORT,
                                                        1620))

        logger.info("          Listening on %s:%s" % (self._bind_ip, self._bind_port))
        logger.info("          Enabled traps: %s" % str(self._enabled_traps))
        logger.info("          Enabled MIBS: %s" % str(self._enabled_MIBS))

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(SNMPtraps, self).shutdown()