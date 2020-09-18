# Copyright (c) 2019-2020 Seagate Technology LLC and/or its Affiliates
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
 *****************************************************************************
  Description:        This is a SNMP trap and inform receiver, it receives all
                v1/v2c/v3 traps or informs from configured devices like switch
                and redirects it to the appropriate msg handler
 *****************************************************************************
"""

import json
import os
import time
import socket

from framework.base.module_thread import SensorThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.utils.severity_reader import SeverityReader
from framework.base.sspl_constants import ServiceTypes, COMMON_CONFIGS

# Modules that receive messages from this module 
from framework.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from message_handlers.logging_msg_handler import LoggingMsgHandler

from json_msgs.messages.sensors.snmp_trap import SNMPtrapMsg

import pysmi
from pysnmp.entity import engine, config
from pysnmp.carrier.asyncore.dgram import udp, udp6
from pysnmp.entity.rfc3413 import ntfrcv
from pysnmp.proto.api import v2c
from pysnmp.smi import builder, view, compiler

from zope.interface import implementer
from sensors.INode_data import INodeData

@implementer(INodeData)
class SNMPtraps(SensorThread, InternalMsgQ):

    SENSOR_NAME       = "SNMPtraps"
    PRIORITY          = 1

    SYSTEM_INFORMATION = "SYSTEM_INFORMATION"
    SITE_ID = "site_id"
    CLUSTER_ID = "cluster_id"
    NODE_ID = "node_id"
    RACK_ID = "rack_id"
    # Section and keys in configuration file
    SNMPTRAPS         = SENSOR_NAME.upper()
    ENABLED_TRAPS     = 'enabled_traps'
    BIND_IP           = 'bind_ip'
    BIND_PORT         = 'bind_port'
    ENABLED_MIBS      = 'enabled_MIBS'

    # Dependency list
    DEPENDENCIES = {
                    "plugins": [],
                    "rpms": []
    }


    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return SNMPtraps.SENSOR_NAME

    @staticmethod
    def dependencies():
        """Returns a list of plugins and RPMs this module requires
           to function.
        """
        return SNMPtraps.DEPENDENCIES

    def __init__(self):
        super(SNMPtraps, self).__init__(self.SENSOR_NAME, self.PRIORITY)
        self._latest_trap = {}

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(SNMPtraps, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(SNMPtraps, self).initialize_msgQ(msgQlist)

        self._set_debug(True)
        self._set_debug_persist(True)
        self.conf_reader = conf_reader
        self._get_config()

        return True

    def read_data(self):
        """Return the most recent trap information"""
        return self._latest_trap

    # def run(self):
    #     """Run the sensor on its own thread"""

    #     # Check for debug mode being activated/deactivated
    #     self._read_my_msgQ_noWait()

    #     try:
    #         #self._log_debug("Start processing")
    #         logger.debug("Start processing")
    #         logger.info("Start processing")
    #         # Create MIB loader to lookup oids sent in traps
    #         # self._mib_builder()
    #         # logger.info(" successfully exited from _mib_builder() ")

    #         # to socket transport dispatcher
    #         snmpEngine = engine.SnmpEngine(v2c.OctetString(hexValue='80001f8880ec70e17424be1f5f00000000'))
    #         logger.info("snmp engine created")
    #         # Transport setup
    #         # UDP over IPv4
    #         config.addTransport(
    #             snmpEngine,
    #             udp.domainName,
    #             udp.UdpTransport().openServerMode((self._bind_ip, self._bind_port))
    #         )
    #         logger.info('udp4 binded')

    #         # UDP over IPv6
    #         # config.addTransport(
    #         #     snmpEngine,
    #         #     udp6.domainName,
    #         #     udp6.Udp6Transport().openServerMode(('::1', self._bind_port))
    #         # )
    #         # logger.info('udp6 binded')
    #         # SNMPv3/USM setup
    #         # this USM entry is used for TRAP receiving purpose 
    #         config.addV3User(snmpEngine, 'inform_sender', 
    #             config.usmHMACSHAAuthProtocol, 'authpass',
    #             config.usmAesCfb128Protocol, 'privpass',
    #         )
    #         logger.info("snmp v3 user added")
    #         # Create an asynchronous dispatcher and register a callback method to handle incoming traps
    #         # Register SNMP Application at the SNMP engine
    #         ntfrcv.NotificationReceiver(snmpEngine, self._trap_catcher)
    #         logger.info("callback function registered.")

    #         snmpEngine.transportDispatcher.jobStarted(1)  # this job would never finish
    #         logger.info("transport Dispatcher job Started")
    #         # Run I/O dispatcher which would receive queries and send confirmations
    #         try:
    #             # Dispatcher will never finish as job #1 never reaches zero
    #             snmpEngine.transportDispatcher.runDispatcher()
    #             logger.info("transport Dispatcher run dispatcher()")
    #         except Exception as ae:
    #             #self._log_debug("Exception: %r" % ae)
    #             logger.debug("Exception: %r" % ae)
    #             logger.info("Exception : %r" % ae)
    #             snmpEngine.transportDispatcher.closeDispatcher()

    #         #self._log_debug("Finished processing, restarting SNMP listener")
    #         logger.debug("Finished processing, restarting SNMP listener")
    #         logger.info("Finished processing, restarting SNMP listener")

    #         # Reset debug mode if persistence is not enabled
    #         self._disable_debug_if_persist_false()

    #         # Schedule the next time to run thread
    #         self._scheduler.enter(10, self._priority, self.run, ())

    #     # Could not bind to IP:port, log it and exit out module
    #     except Exception as ae:
    #         self._log_debug("Unable to process SNMP traps from this node, closing module.")
    #         self._log_debug(f"SNMP Traps sensor attempted to bind to {self._bind_ip}:{self._bind_port}")
    #         logger.info("Unable to process SNMP traps from this node, closing module.")
    #         logger.info(f"SNMP Traps sensor attempted to bind to {self._bind_ip}:{self._bind_port}")
    #         logger.info("Exception : %r " % ae)

    def run(self):
        try:
            logger.info("Start of run()")
            #self._mib_builder()
            #logger.info("exited from mib builder")
            snmpEngine = engine.SnmpEngine(v2c.OctetString(hexValue='80001f8880ec70e17424be1f5f00000000'))
            logger.info("snmpEngine regiestered.")
            config.addTransport(
                snmpEngine,
                udp.domainName,
                udp.UdpTransport().openServerMode((self._bind_ip, self._bind_port))
            )
            logger.info("upd4 registered at %s:%s" %self._bind_ip, self._bind_port)
            config.addV3User(snmpEngine, 'inform_sender', 
                config.usmHMACSHAAuthProtocol, 'authpass',
                config.usmAesCfb128Protocol, 'privpass',
            )
            logger.info("v3 user registered")
            # Register SNMP Application at the SNMP engine
            ntfrcv.NotificationReceiver(snmpEngine, self.cbFun)

            snmpEngine.transportDispatcher.jobStarted(1)  # this job would never finish

            # Run I/O dispatcher which would receive queries and send confirmations
            try:
                snmpEngine.transportDispatcher.runDispatcher()
            except Exception as ae:
                logger.error("Exception : %r" %ae)
                snmpEngine.transportDispatcher.closeDispatcher()
                raise
            logger.info("run() methond finished. restarting SNMP")
            self._scheduler.enter(10, self._priority, self.run, ())

        except Exception as ae:
            logger.error("Exception : %r" %ae)

    def cbFun(self, snmpEngine, stateReference, contextEngineId, contextName, varBinds, cbCtx):
        logger.info('Notification from ContextEngineId "%s", ContextName "%s"' % (contextEngineId.prettyPrint(), contextName.prettyPrint()))
        for name, val in varBinds:
            logger.info('%s = %s' % (name.prettyPrint(), val.prettyPrint()))

    def _mib_builder(self):
        """Loads the MIB files and creates dicts with hierarchical structure"""
        os.system('chown sspl-ll -R /home/sspl-ll/*')
        # Create MIB loader/builder
        mibBuilder = builder.MibBuilder()

        self._log_debug('Reading MIB sources...')
        logger.info('Reading MIB sources...')
        compiler.addMibCompiler(mibBuilder, sources=['/etc/sspl-ll/templates/snmp'])
        # mibSources = mibBuilder.getMibSources() + (
        #     builder.DirMibSource('/etc/sspl-ll/templates/snmp'),)
        # mibBuilder.setMibSources(*mibSources)

        self._log_debug("MIB sources: %s" % str(mibBuilder.getMibSources()))
        logger.info("MIB sources: %s" % str(mibBuilder.getMibSources()))
        # for module in self._enabled_MIBS:
        #     mibBuilder.loadModules(module)
        mibBuilder.loadModules('IF-MIB', 'LM-SENSORS-MIB', 'DISMAN-EVENT-MIB', 'SNMPv2-MIB', 'HOST-RESOURCES-MIB')
        #mibBuilder.loadModules(self._enabled_MIBS)
        logger.info("All mib modules loaded.")
        self._mibView = view.MibViewController(mibBuilder)

    def _mib_oid_value(self, oid, val):
        """Look up the trap name using the OID in the MIB"""
        ret_val = "N/A"
        nodeDesc = "N/A"
        try:
            # Retrieve information in MIB using the OID
            modName, nodeDesc, suffix = self._mibView.getNodeLocation(oid)
            ret_val = val
            self._log_debug(f'module: {modName}, {nodeDesc}: <{type(val).__name__}> {val.prettyPrint()}, oid: {oid.prettyPrint()}')
            logger.info(f'module: {modName}, {nodeDesc}: <{type(val).__name__}> {val.prettyPrint()}, oid: {oid.prettyPrint()}')
            # Lookup the trap name from the SNMP Modules MIB
            if(type(val).__name__ == 'ObjectIdentifier'):
                # Convert the dot notated str oid to a tuple of ints for getNodeName API call
                trap_oid = str(val)
                tmp_oid = trap_oid.split(".")
                tuple_oid = tuple([int(x) for x in tmp_oid])

                oid, label, suffix = self._mibView.getNodeName(tuple_oid)
                self._trap_name = str(label[-1]) + '.'.join(tuple([str(x) for x in suffix]))
                self._log_debug(f'Trap Notification: {self._trap_name}')
                logger.info(f'Trap Notification: {self._trap_name}')
        except Exception as ae:
            self._log_debug("_mib_oid_value: %r" % ae)
            logger.info("_mib_oid_value: %r" % ae)
        return (nodeDesc, ret_val)

    def _trap_catcher(self,snmpEngine, stateReference, contextEngineId, contextName, varBinds, cbCtx):
        """Callback method when a SNMP trap arrives"""
        json_data = {}
        self._trap_name = ""

        logger.info('Notification from ContextEngineId "%s", ContextName "%s"' % (contextEngineId.prettyPrint(), contextName.prettyPrint()))
        for oid, val in varBinds:
            # nodeDesc, ret_val = self._mib_oid_value(oid, val)
            nodeDesc, ret_val = oid, val
            logger.info(f"{oid} => {val}")
            # Build up JSON data to be logged in IEM and sent to Halon
            if nodeDesc != "N/A" and ret_val != "N/A":
                json_data[nodeDesc] = ret_val

        self._log_debug(f"trap_name: {self._trap_name}")
        self._log_debug(f"enabled_traps: {self._enabled_traps}")
        logger.info("trap_name: {self._trap_name}")
        logger.info(f"enabled_traps: {self._enabled_traps}")

        # Apply filter unless there is an asterisk in the list
        if '*' in self._enabled_traps or self._trap_name in self._enabled_traps:
            # Log IEM
            self._log_iem(json_data)

            # Transmit to Halon
            self._transmit_json_msg(json_data)

    def _gen_json_msg(self, alert_type, details):
        severity_reader = SeverityReader()
        severity = severity_reader.map_severity(alert_type)
        epoch_time = str(int(time.time()))

        #alert_id = self._get_alert_id(epoch_time)
        #resource_id = ext.get("durable-id")
        host_name = socket.gethostname()

        info = {
                "site_id": self.site_id,
                "cluster_id": self.cluster_id,
                "rack_id": self.rack_id,
                "node_id": self.node_id,
                #"resource_type": self.RESOURCE_TYPE,
                #"resource_id": resource_id,
                "event_time": epoch_time
                }
        specific_info = json.dumps(details, sort_keys=True)

        json_msg = json.dumps(
            {"sensor_request_type" : {
                "enclosure_alert" : {
                    "status": "update",
                    "host_id": host_name,
                    "alert_type": alert_type,
                    "severity": severity,
                    #"alert_id": alert_id,
                    "info": info,
                    "specific_info": specific_info
                },
            }})

        return json_msg

    def _log_iem(self, json_data):
        """Create IEM and send to logging msg handler"""
        # log_msg = f"IEC: 020004001: SNMP Trap Received, {self._trap_name}"
        # internal_json_msg = json.dumps(
        #             {"actuator_request_type" : {
        #                 "logging": {
        #                     "log_level": "LOG_WARNING",
        #                     "log_type": "IEM",
        #                     "log_msg": f"{log_msg}:{json.dumps(json_data, sort_keys=True)}"
        #                     }
        #                 }
        #              })
        internal_json_msg = self._gen_json_msg("threshold_breached:high",json_data)

        # Send the event to logging msg handler to send IEM message to journald
        self._write_internal_msgQ(LoggingMsgHandler.name(), internal_json_msg)

    def _transmit_json_msg(self, json_data):
        """Transmit message to halon by passing it to egress msg handler"""
        json_data["trapName"] = self._trap_name
        json_msg = SNMPtrapMsg(self._gen_json_msg("threshold_breached:high",json_data)).getJson()
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

    def _get_config(self):
        """Retrieves the information in /etc/sspl.conf"""
        self._enabled_traps = ['*']
        self._enabled_MIBS = ['AGENTX-MIB.txt',  'IF-MIB.txt', 'NET-SNMP-EXAMPLES-MIB.txt',  'SCTP-MIB.txt', 'SNMPv2-TC.txt',
            'BRIDGE-MIB.txt', 'INET-ADDRESS-MIB.txt', 'NET-SNMP-EXTEND-MIB.txt', 'SMUX-MIB.txt', 'SNMPv2-TM.txt',
            'DISMAN-EVENT-MIB.txt', 'IP-FORWARD-MIB.txt', 'NET-SNMP-MIB.txt', 'SNMP-COMMUNITY-MIB.txt', 'SNMP-VIEW-BASED-ACM-MIB.txt',
            'DISMAN-SCHEDULE-MIB.txt', 'IP-MIB.txt', 'NET-SNMP-PASS-MIB.txt', 'SNMP-FRAMEWORK-MIB.txt', 'TCP-MIB.txt', 
            'DISMAN-SCRIPT-MIB.txt', 'IPV6-FLOW-LABEL-MIB.txt', 'NET-SNMP-TC.txt', 'SNMP-MPD-MIB.txt', 'TRANSPORT-ADDRESS-MIB.txt',
            'EtherLike-MIB.txt', 'IPV6-ICMP-MIB.txt', 'NET-SNMP-VACM-MIB.txt', 'SNMP-NOTIFICATION-MIB.txt', 'TUNNEL-MIB.txt',
            'HCNUM-TC.txt', 'IPV6-MIB.txt', 'NETWORK-SERVICES-MIB.txt',   'SNMP-PROXY-MIB.txt', 'UCD-DEMO-MIB.txt',
            'HOST-RESOURCES-MIB.txt', 'IPV6-TCP-MIB.txt','NOTIFICATION-LOG-MIB.txt',   'SNMP-TARGET-MIB.txt', 'UCD-DISKIO-MIB.txt',
            'HOST-RESOURCES-TYPES.txt', 'IPV6-TC.txt', 'SNMP-USER-BASED-SM-MIB.txt',   'UCD-DLMOD-MIB.txt',
            'IANA-ADDRESS-FAMILY-NUMBERS-MIB.txt',  'IPV6-UDP-MIB.txt', 'SNMP-USM-AES-MIB.txt', 'UCD-IPFWACC-MIB.txt',
            'IANAifType-MIB.txt', 'LM-SENSORS-MIB.txt', 'RFC1155-SMI.txt', 'SNMP-USM-DH-OBJECTS-MIB.txt', 'UCD-SNMP-MIB.txt',
            'IANA-LANGUAGE-MIB.txt', 'RFC1213-MIB.txt', 'SNMPv2-CONF.txt', 'UDP-MIB.txt',
            'IANA-RTPROTO-MIB.txt', 'MTA-MIB.txt', 'RFC-1215.txt', 'SNMPv2-MIB.txt',
            'IF-INVERTED-STACK-MIB.txt', 'NET-SNMP-AGENT-MIB.txt', 'RMON-MIB.txt', 'SNMPv2-SMI.txt']
        self._bind_ip = '10.230.240.148'
        self._bind_port = 162
        # self._enabled_traps = self._conf_reader._get_value_list(self.SNMPTRAPS,
        #                                                 self.ENABLED_TRAPS)
        # self._enabled_MIBS  = self._conf_reader._get_value_list(self.SNMPTRAPS,
        #                                                 self.ENABLED_MIBS)

        # self._bind_ip = self._conf_reader._get_value_with_default(self.SNMPTRAPS,
        #                                                 self.BIND_IP,
        #                                                 'service')
        # self._bind_port = int(self._conf_reader._get_value_with_default(self.SNMPTRAPS,
        #                                                 self.BIND_PORT,
        #                                                 1620))
        self.site_id = self.conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.SITE_ID),
                                                '001')
        self.rack_id = self.conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.RACK_ID),
                                                '001')
        self.node_id = self.conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.NODE_ID),
                                                '001')
        # Need to keep cluster_id string here to generate decryption key
        self.cluster_id = self.conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.CLUSTER_ID),
                                                '001')

        logger.info("          Listening on %s:%s" % (self._bind_ip, self._bind_port))
        logger.info("          Enabled traps: %s" % str(self._enabled_traps))
        logger.info("          Enabled MIBS: %s" % str(self._enabled_MIBS))

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(SNMPtraps, self).shutdown()
