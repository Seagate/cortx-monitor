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
 ****************************************************************************
  Description:       Generates disk alerts on faults, presence state changes,
                    detected by polling disks and system state using Realstor
                    Management Controller CLI APIs
 ****************************************************************************
"""

import json
import time
import socket
import uuid
from threading import Event
import re

from framework.base.module_thread import SensorThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.utils.severity_reader import SeverityReader
from framework.platforms.realstor.realstor_enclosure import singleton_realstorencl
from framework.utils.store_factory import store

# Modules that receive messages from this module
from message_handlers.real_stor_encl_msg_handler import RealStorEnclMsgHandler
from message_handlers.logging_msg_handler import LoggingMsgHandler

from zope.interface import implementer
from sensors.IRealStor_disk_sensor import IRealStorDiskSensor
from framework.utils.conf_utils import *


@implementer(IRealStorDiskSensor)
class RealStorDiskSensor(SensorThread, InternalMsgQ):
    """Monitors RealStor enclosure disks state and raise sspl events for
       detected faults, insertion,removal events """


    SENSOR_NAME = "RealStorDiskSensor"
    RESOURCE_TYPE = "enclosure:fru:disk"

    PRIORITY = 1

    RSS_DISK_GET_ALL = "all"

    # Mandatory attributes in disk json data
    disk_generic_info = [ "enclosure-id", "enclosure-wwn", "slot", "description",
                          "architecture", "interface", "serial-number", "size",
                          "vendor", "model", "revision", "temperature", "status",
                          "LED-status", "locator-LED", "blink", "smart",
                          "health", "health-reason", "health-recommendation"
                        ]

    # local resource cache
    latest_disks = {}
    memcache_disks = {}
    DISK_IDENTIFIER = "Disk 0."
    NUMERIC_IDENTIFIER = "numeric"
    invalidate_latest_disks_info = False

    # Dependency list
    DEPENDENCIES = {
                    "plugins": ["RealStorEnclMsgHandler"],
                    "rpms": []
    }

    @staticmethod
    def name():
        """@return: name of the module."""
        return RealStorDiskSensor.SENSOR_NAME

    @staticmethod
    def dependencies():
        """Returns a list of plugins and RPMs this module requires
           to function.
        """
        return RealStorDiskSensor.DEPENDENCIES

    def __init__(self):
        super(RealStorDiskSensor, self).__init__(self.SENSOR_NAME,
                                                    self.PRIORITY)
        self.last_alert = None

        self.rssencl = singleton_realstorencl

        # disks persistent cache
        self.disks_prcache = f"{self.rssencl.frus}disks/"

        self.pollfreq_disksensor = \
            int(Conf.get(SSPL_CONF, f"{self.rssencl.CONF_REALSTORDISKSENSOR}>{POLLING_FREQUENCY_OVERRIDE}",
                        0))

        if self.pollfreq_disksensor == 0:
                self.pollfreq_disksensor = self.rssencl.pollfreq

        # Flag to indicate suspension of module
        self._suspended = False

        self._event = None
        self._event_wait_results = set()

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RealStorDiskSensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RealStorDiskSensor, self).initialize_msgQ(msgQlist)

        return True

    def read_data(self):
        """Return the last raised alert, none otherwise"""
        return self.last_alert

    def run(self):
        """Run disk monitoring periodically on its own thread."""

        # Do not proceed if module is suspended
        if self._suspended == True:
            self._scheduler.enter(self.pollfreq_disksensor, self._priority, self.run, ())
            return

        # Allow RealStor Encl MC to start services.
        #time.sleep(self.rssencl.REALSTOR_MC_BOOTWAIT)

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        try:
            # poll all disk status and raise events if
            # insertion/removal detected
            self._rss_check_disks_presence()

            #Do not proceed further if latest disks info can't be validated due to store function error
            if not self.invalidate_latest_disks_info:
                # Polling system status
                self.rssencl.get_system_status()

                # check for disk faults & raise if found
                self._rss_check_disk_faults()
            else:
                logger.warn("Can not validate disk faults or presence due to persistence store error")

        except Exception as ae:
            logger.exception(ae)

        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()

        # Fire every configured seconds to poll disks status
        self._scheduler.enter(self.pollfreq_disksensor,
          self._priority, self.run, ())

    def _rss_raise_disk_alert(self, alert_type, disk_info):
        """Raise disk alert with supported alert type"""

        #logger.debug("Raise - alert type {0}, info {1}".format(alert_type,disk_info))
        if not disk_info:
            logger.warn("disk_info None, ignoring")
            return

        if alert_type not in self.rssencl.fru_alerts:
            logger.error(f"Supplied alert type [{alert_type}] not supported")
            return

        # form json with default values
        disk = dict.fromkeys(self.disk_generic_info, "NA")
        disk['slot'] = -1
        disk['blink'] = 0
        disk['enclosure-id'] = 0

        # Build data for must fields in fru disk data
        for item in self.disk_generic_info:
            if item in disk_info:
                disk[item] = disk_info[item]

        encl = self.rssencl.ENCL_FAMILY
        disk[encl] = self.rssencl.LDR_R1_ENCL

        # Build data for platform specific fields in fru disk data
        # get remaining extra key value pairs from passed disk_info
        extended_info = {key:disk_info[key] for key in disk_info if key not in\
                            disk and self.NUMERIC_IDENTIFIER not in key}

        # notify realstor encl msg handler
        self._send_json_msg(alert_type, disk, extended_info)

        # send IEM
        self._log_IEM(alert_type, disk, extended_info)

    def _rss_check_disks_presence(self):
        """Match cached realstor disk info with latest retrieved disks info """

        self.rss_cliapi_poll_disks(self.RSS_DISK_GET_ALL)

        if not self.memcache_disks:
            if self.rssencl.active_ip != self.rssencl.ws.LOOPBACK:
                logger.warn("Last polled drives info in-memory cache "
                    "unavailable , unable to check drive presence change")
                return

        if not self.latest_disks:
            if self.rssencl.active_ip != self.rssencl.ws.LOOPBACK:
                logger.warn("Latest polled drives info in-memory cache "
                    "unavailable, unable to check drive presence change")
            return

        # keys are disk slot numbers
        removed_disks = set(self.memcache_disks.keys()) - set(self.latest_disks.keys())
        inserted_disks = set(self.latest_disks.keys()) - set(self.memcache_disks.keys())

        # get populated slots in both caches
        populated = set(self.memcache_disks.keys()) & set(self.latest_disks.keys())

        # check for replaced disks
        for slot in populated:
            if self.memcache_disks[slot]['serial-number'] != self.latest_disks[slot]['serial-number']:

                if slot not in removed_disks:
                    removed_disks.add(slot)

                if slot not in inserted_disks:
                    inserted_disks.add(slot)

        # If no difference seen between cached & latest set of disk list,
        # means no disk removal or insertion happened
        if not (removed_disks or inserted_disks):
            #logger.info("Disk presence state _NOT_ changed !!!")
            return

        self._event = Event()
        for slot in removed_disks:
            #get removed drive data from disk cache
            disk_datafile = f"{self.disks_prcache}disk_{slot}.json.prev"

            path_exists, _ = store.exists(disk_datafile)
            if not path_exists:
                disk_datafile = f"{self.disks_prcache}disk_{slot}.json"

            disk_info = store.get(disk_datafile)

            #raise alert for missing drive
            self._rss_raise_disk_alert(self.rssencl.FRU_MISSING, disk_info)
            # Wait till msg is sent to rabbitmq or added in consul for resending.
            # If timed out, do not update cache
            if self._event.wait(self.rssencl.PERSISTENT_DATA_UPDATE_TIMEOUT):
                store.delete(disk_datafile)
            self._event.clear()
        self._event = None

        for slot in inserted_disks:
            #get inserted drive data from disk cache
            disk_info = store.get(f"{self.disks_prcache}disk_{slot}.json")

            #raise alert for added drive
            self._rss_raise_disk_alert(self.rssencl.FRU_INSERTION, disk_info)

        # Update cached disk data after comparison
        self.memcache_disks = self.latest_disks
        self.rssencl.memcache_frus.update({"disks":self.memcache_disks})

        return

    def rss_cliapi_poll_disks(self, disk):
        """Retreive realstor disk info using cli api /show/disks"""

        # make ws request
        url = self.rssencl.build_url(
                  self.rssencl.URI_CLIAPI_SHOWDISKS)

        if(disk != self.RSS_DISK_GET_ALL):
           diskId = disk.partition("0.")[2]

           if(diskId.isdigit()):
               url = f"{url}/{disk}"
        url = f"{url}/detail"

        response = self.rssencl.ws_request(
                        url, self.rssencl.ws.HTTP_GET)

        if not response:
            logger.warn(f"{self.rssencl.LDR_R1_ENCL}:: Disks status unavailable as ws request {url} failed")
            return

        if response.status_code != self.rssencl.ws.HTTP_OK:
            if url.find(self.rssencl.ws.LOOPBACK) == -1:
                logger.error(f"{self.rssencl.LDR_R1_ENCL}:: http request {url} to poll disks failed with \
                       err {response.status_code}")
            return

        try:
            jresponse = json.loads(response.content)
        except ValueError as badjson:
            logger.error(f"{url} returned mal-formed json:\n{badjson}")

        if jresponse:
            api_resp = self.rssencl.get_api_status(jresponse['status'])
            #logger.debug("%s api response:%d" % (url.format(),api_resp))

            if ((api_resp == -1) and
                   (response.status_code == self.rssencl.ws.HTTP_OK)):
                logger.warn("/show/disks api response unavailable, "
                    "marking success as http code is 200")
                api_resp = 0

            if api_resp == 0:
                drives = jresponse['drives']

                # reset latest drive cache to build new
                self.latest_disks = {}
                self.invalidate_latest_disks_info = False

                for drive in drives:
                    slot = drive.get("slot", -1)
                    sn = drive.get("serial-number", "NA")
                    health = drive.get("health", "NA")

                    if slot != -1:
                        self.latest_disks[slot] = {"serial-number":sn, "health":health}

                        #dump drive data to persistent cache
                        dcache_path = f"{self.disks_prcache}disk_{slot}.json"

                        # If drive is replaced, previous drive info needs
                        # to be retained in disk_<slot>.json.prev file and
                        # then only dump new data to disk_<slot>.json
                        path_exists, ret_val = store.exists(dcache_path)
                        if path_exists and ret_val == "Success":
                            prevdrive = store.get(dcache_path)

                            if prevdrive is not None:
                                prevsn = prevdrive.get("serial-number","NA")
                                prevhealth = prevdrive.get("health", "NA")

                                if prevsn != sn or prevhealth != health:
                                    # Rename path
                                    store.put(store.get(dcache_path), dcache_path + ".prev")
                                    store.delete(dcache_path)

                                    store.put(drive, dcache_path)
                        elif not path_exists and ret_val == "Success":
                            store.put(drive, dcache_path)
                        else:
                            # Invalidate latest disks info if persistence store error encountered
                            logger.warn(f"store.exists {dcache_path} return value {ret_val}")
                            self.invalidate_latest_disks_info = True
                            break

                if self.invalidate_latest_disks_info is True:
                    # Reset latest disks info
                    self.latest_disks = {}

            #If no in-memory cache, build from persistent cache
            if not self.memcache_disks:
                self._rss_build_disk_cache_from_persistent_cache()

            # if no memory cache still
            if not self.memcache_disks:
                self.memcache_disks = self.latest_disks


    def _rss_build_disk_cache_from_persistent_cache(self):
        """Retreive realstor system state info using cli api /show/system"""

        files = store.get_keys_with_prefix(self.disks_prcache)

        if not files:
            logger.debug("No files in Disk cache folder, ignoring")
            return

        for filename in files:
            if filename.startswith('disk_') and filename.endswith('.json'):
                if f"{filename}.prev" in files:
                    filename = f"{filename}.prev"
                drive = store.get(self.disks_prcache + filename)
                slotstr = re.findall("disk_(\d+).json", filename)[0]

                if not slotstr.isdigit():
                    logger.debug(f"slot {slotstr} not numeric, ignoring")
                    continue

                slot = int(slotstr)

                if drive :
                    sn = drive.get("serial-number","NA")
                    self.memcache_disks[slot] = {"serial-number":sn}

        #logger.debug("Disk cache built from persistent cache {0}".
        #    format(self.memcache_disks))

    def _rss_check_disk_faults(self):
        """Retreive realstor system state info using cli api /show/system"""

        if not self.rssencl.check_system_faults_changed():
            #logger.debug("System faults state _NOT_ changed !!! ")
            return

        try:
            # Extract new system faults
            faults = self.rssencl.latest_faults
            # TODO optimize to avoid nested 'for' loops.
            # Second 'for' loop in check_new_fault()
            self._event = Event()
            if faults:
                for fault in faults:

                    #logger.debug("Faulty component-id {0}, IDENT {1}"\
                    #    .format(fault["component-id"], self.DISK_IDENTIFIER))

                    # Check faulting component type
                    if self.DISK_IDENTIFIER in fault["component-id"]:
                        # If fault on disk, get disk full info including health
                        if self.rssencl.check_new_fault(fault):

                            # Extract slot from "component-id":"Disk 0.39"
                            slot = fault["component-id"].split()[1].split('.')[1]

                            # Alert send only if disks_prcache updated with latest disk data
                            if self.latest_disks[int(slot)]["health"] != "OK":
                                #get drive data from disk cache
                                disk_info = store.get(
                                    self.disks_prcache+"disk_{0}.json".format(slot))

                                # raise alert for disk fault
                                self._rss_raise_disk_alert(self.rssencl.FRU_FAULT, disk_info)
                                # To ensure all msg is sent to rabbitmq or added in consul for resending.
                                self._event_wait_results.add(
                                    self._event.wait(self.rssencl.PERSISTENT_DATA_UPDATE_TIMEOUT))
                                self._event.clear() 

            # Check for resolved faults
            for cached in self.rssencl.memcache_faults:
                if not any(d.get("component-id", None) == cached["component-id"] \
                    for d in self.rssencl.latest_faults) and self.DISK_IDENTIFIER in cached["component-id"]:

                    # Extract slot from "component-id":"Disk 0.39"
                    logger.info(f"Found resolved disk fault for {cached['component-id']}")
                    slot = cached["component-id"].split()[1].split('.')[1]

                    # Alert send only if disks_prcache updated with latest disk data
                    if self.latest_disks[int(slot)]["health"] == "OK":
                        # get drive data from disk cache
                        disk_info = store.get(
                            self.disks_prcache+"disk_{0}.json".format(slot))
                        # raise alert for resolved disk fault
                        self._rss_raise_disk_alert(self.rssencl.FRU_FAULT_RESOLVED, disk_info)
                        # To ensure all msg is sent to rabbitmq or added in consul for resending.
                        self._event_wait_results.add(
                                    self._event.wait(self.rssencl.PERSISTENT_DATA_UPDATE_TIMEOUT))
                        self._event.clear()
            # If all messages are sent to rabbitmq or added in consul for resending.
            # then only update cache
            if self._event_wait_results and all(self._event_wait_results):
                self.rssencl.update_memcache_faults()
            self._event_wait_results.clear()
            self._event = None

        except Exception as e:
            logger.exception(f"Error in _rss_check_disk_faults {e}")

    def _gen_json_msg(self, alert_type, details, ext):
        """ Generate json message"""

        severity_reader = SeverityReader()
        severity = severity_reader.map_severity(alert_type)
        epoch_time = str(int(time.time()))

        alert_id = self._get_alert_id(epoch_time)
        resource_id = ext.get("durable-id")
        host_name = socket.gethostname()

        info = {
                "site_id": self.rssencl.site_id,
                "cluster_id": self.rssencl.cluster_id,
                "rack_id": self.rssencl.rack_id,
                "node_id": self.rssencl.node_id,
                "resource_type": self.RESOURCE_TYPE,
                "resource_id": resource_id,
                "event_time": epoch_time
                }
        specific_info = dict()
        specific_info.update(details)
        specific_info.update(ext)

        for k in specific_info.keys():
            if specific_info[k] == "":
                specific_info[k] = "N/A"


        json_msg = json.dumps(
            {"sensor_request_type" : {
                "enclosure_alert" : {
                    "status": "update",
                    "host_id": host_name,
                    "alert_type": alert_type,
                    "severity": severity,
                    "alert_id": alert_id,
                    "info": info,
                    "specific_info": specific_info
                },
            }})

        return json_msg

    def _get_alert_id(self, epoch_time):
        """Returns alert id which is a combination of
           epoch_time and salt value
        """
        salt = str(uuid.uuid4().hex)
        alert_id = epoch_time + salt
        return alert_id

    def _send_json_msg(self, alert_type, details, ext):
        """Transmit alert data to RealStorEnclMsgHandler to be processed
        and sent out
        """

        internal_json_msg = self._gen_json_msg(alert_type, details, ext)
        self.last_alert = internal_json_msg
        # RAAL stands for - RAise ALert
        logger.info(f"RAAL: {internal_json_msg}")
        # Send the event to storage encl message handler to generate json message and send out
        self._write_internal_msgQ(RealStorEnclMsgHandler.name(), internal_json_msg, self._event)

    def _log_IEM(self, alert_type, details, ext):
        """Sends an IEM to logging msg handler"""
        json_data = self._gen_json_msg(alert_type, details, ext)

        # Send the event to storage encl message handler to generate json message
        # and send out
        internal_json_msg=json.dumps(
                {'actuator_request_type':
                    {'logging':
                        {'log_level': 'LOG_WARNING', 'log_type': 'IEM',
                          'log_msg': f'{json_data}'}
                    }
                })

        # Send the event to logging msg handler to send IEM message to journald
        self._write_internal_msgQ(LoggingMsgHandler.name(), internal_json_msg)

    def suspend(self):
        """Suspends the module thread. It should be non-blocking"""
        super(RealStorDiskSensor, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(RealStorDiskSensor, self).resume()
        self._suspended = False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RealStorDiskSensor, self).shutdown()
