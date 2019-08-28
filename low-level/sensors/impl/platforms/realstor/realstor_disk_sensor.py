"""
 ****************************************************************************
 Filename:          realstor_disk_sensor.py
 Description:       Generates disk alerts on faults, presence state changes,
                    detected by polling disks and system state using Realstor
                    Management Controller CLI APIs
 Creation Date:     06/04/2019
 Author:            Chetan S. Deshmukh

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import os
import threading
import json
import time
import errno

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.platforms.realstor.realstor_enclosure import singleton_realstorencl

# Modules that receive messages from this module
from message_handlers.real_stor_encl_msg_handler import RealStorEnclMsgHandler
from message_handlers.logging_msg_handler import LoggingMsgHandler

from zope.interface import implements
from sensors.IRealStor_disk_sensor import IRealStorDiskSensor

class RealStorDiskSensor(ScheduledModuleThread, InternalMsgQ):
    """Monitors RealStor enclosure disks state and raise sspl events for
       detected faults, insertion,removal events """

    implements(IRealStorDiskSensor)

    SENSOR_NAME = "RealStorDiskSensor"
    SENSOR_RESP_TYPE = "enclosure_disk_alert"
    RESOURCE_CATEGORY = "fru"

    PRIORITY          = 1

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


    @staticmethod
    def name():
        """@return: name of the module."""
        return RealStorDiskSensor.SENSOR_NAME

    def __init__(self):
        super(RealStorDiskSensor, self).__init__(self.SENSOR_NAME,
                                                    self.PRIORITY)
        self.last_alert = None

        self.rssencl = singleton_realstorencl

        # disks persistent cache
        self.disks_prcache = self.rssencl.frus + "disks/"

        self.pollfreq_disksensor = \
            int(self.rssencl.conf_reader._get_value_with_default(\
                self.rssencl.CONF_REALSTORDISKSENSOR,\
                "polling_frequency_override", 0))

        if self.pollfreq_disksensor == 0:
                self.pollfreq_disksensor = self.rssencl.pollfreq

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RealStorDiskSensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RealStorDiskSensor, self).initialize_msgQ(msgQlist)

        # check for disk persistent cache
        self.rssencl.check_prcache(self.disks_prcache)

    def read_data(self):
        """Return the last raised alert, none otherwise"""
        return self.last_alert

    def run(self):
        """Run disk monitoring periodically on its own thread."""

        # Allow RealStor Encl MC to start services.
        #time.sleep(self.rssencl.REALSTOR_MC_BOOTWAIT)

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        self.rssencl.check_prcache(self.disks_prcache)

        try:
            # poll all disk status and raise events if
            # insertion/removal detected
            self._rss_check_disks_presence()

            # Polling system status
            self.rssencl.get_system_status()

            # check for disk faults & raise if found
            self._rss_check_disk_faults()

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
            logger.error("Supplied alert type [%s] not supported" % alert_type)
            return

        # form json with default values
        disk = dict.fromkeys(self.disk_generic_info, "NA")
        disk['slot'] = -1
        disk['blink'] = 0
        disk['enclosure-id'] = 0

        # Build data for must fields in fru disk data
        for item in self.disk_generic_info:
            if disk_info.has_key(item):
                disk[item] = disk_info[item]

        encl = self.rssencl.ENCL_FAMILY
        disk[encl] = self.rssencl.EES_ENCL

        # Build data for platform specific fields in fru disk data
        # get remaining extra key value pairs from passed disk_info
        extended_info = {key:disk_info[key] for key in disk_info if key not in\
                            disk and self.NUMERIC_IDENTIFIER not in key}

        disk[self.rssencl.EXTENDED_INFO] = extended_info

        # notify realstor encl msg handler
        self._send_json_msg(alert_type, disk, extended_info)

        # send IEM
        self._log_IEM(alert_type, disk, extended_info)

    def _rss_check_disks_presence(self):
        """Match cached realstor disk info with latest retrieved disks info """

        self.rss_cliapi_poll_disks(self.RSS_DISK_GET_ALL)

        if not self.memcache_disks:
            logger.warn("Last polled drives info in-memory cache unavailable"
                        ", unable to check drive presence change")
            return

        if not self.latest_disks:
            logger.warn("Latest polled drives info in-memory cache unavailable"
                        ", unable to check drive presence change")
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

        for slot in removed_disks:
            #get removed drive data from disk cache
            disk_datafile = self.disks_prcache+"disk_{0}.json.prev".format(slot)

            if not os.path.exists(disk_datafile):
                disk_datafile = self.disks_prcache+"disk_{0}.json".format(slot)

            disk_info = self.rssencl.jsondata.load(disk_datafile)

            #raise alert for missing drive
            self._rss_raise_disk_alert(self.rssencl.FRU_MISSING, disk_info)

            os.remove(disk_datafile)

        for slot in inserted_disks:
            #get inserted drive data from disk cache
            disk_info = self.rssencl.jsondata.load(
                           self.disks_prcache+"disk_{0}.json".format(slot))

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
               url = url + "/" + disk

        url = url + "/detail"

        response = self.rssencl.ws_request(
                        url, self.rssencl.ws.HTTP_GET)

        if not response:
            logger.warn("{0}:: Disks status unavailable as ws request {1}"
                " failed".format(self.rssencl.EES_ENCL, url))
            return

        if response.status_code != self.rssencl.ws.HTTP_OK:
            logger.error("{0}:: http request {1} to poll disks failed with"
                " err {2}" % self.rssencl.EES_ENCL, url, response.status_code)
            return

        try:
            jresponse = json.loads(response.content)
        except ValueError as badjson:
            logger.error("%s returned mal-formed json:\n%s" % (url, badjson))

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

                for drive in drives:
                    slot = drive.get("slot",-1)
                    sn = drive.get("serial-number","NA")

                    if slot != -1:
                        self.latest_disks[slot] = {"serial-number":sn}

                        #dump drive data to persistent cache
                        dcache_path = self.disks_prcache + \
                                         "disk_{0}.json".format(slot)

                        # If drive is replaced, previous drive info needs
                        # to be retained in disk_<slot>.json.prev file and
                        # then only dump new data to disk_<slot>.json
                        if os.path.exists(dcache_path):
                            prevdrive = self.rssencl.jsondata.load(dcache_path)
                            prevsn = prevdrive.get("serial-number","NA")

                            if prevsn != sn:
                                os.rename(dcache_path,dcache_path + ".prev")

                                self.rssencl.jsondata.dump(drive, dcache_path)
                        else:
                            self.rssencl.jsondata.dump(drive, dcache_path)

            #If no in-memory cache, build from persistent cache
            if not self.memcache_disks:
                self._rss_build_disk_cache_from_persistent_cache()

            # if no memory cache still
            if not self.memcache_disks:
                self.memcache_disks = self.latest_disks


    def _rss_build_disk_cache_from_persistent_cache(self):
        """Retreive realstor system state info using cli api /show/system"""

        if not os.path.exists(self.disks_prcache):
            logger.debug("Disk cache folder doesnt exists, ignoring")
            return

        files = os.listdir(self.disks_prcache)

        if not files:
            logger.debug("No files in Disk cache folder, ignoring")
            return

        for filename in files:
            if filename.startswith('disk_') and filename.endswith('.json'):

                drive = self.rssencl.jsondata.load(self.disks_prcache + filename)
                filename = filename[:-5]
                slotstr = filename.strip('disk_')

                if not slotstr.isdigit():
                    logger.debug("slot {0} not numeric, ignoring".format(slotstr))
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

                            #get drive data from disk cache
                            disk_info = self.rssencl.jsondata.load(
                                self.disks_prcache+"disk_{0}.json".format(slot))

                            # raise alert for disk fault
                            self._rss_raise_disk_alert(self.rssencl.FRU_FAULT, disk_info)

            # Check for resolved faults
            for cached in self.rssencl.memcache_faults:
                if not any(d.get("component-id", None) == cached["component-id"] \
                    for d in self.rssencl.latest_faults):

                    # Extract slot from "component-id":"Disk 0.39"
                    logger.info("Found resolved disk fault for {0}"\
                        .format(cached["component-id"]))
                    slot = cached["component-id"].split()[1].split('.')[1]

                    #get drive data from inmemory disk cache
                    disk_info = self.memcache_disks[slot]

                    # raise alert for resolved disk fault
                    self._rss_raise_disk_alert(self.rssencl.FRU_FAULT_RESOLVED, disk_info)

        except Exception as e:
            logger.exception("Error in _rss_check_disk_faults {0}".format(e))

    def _gen_json_msg(self, alert_type, details, ext):
        """ Generate json message"""

        json_msg = json.dumps(
            {"sensor_request_type" : {
                "enclosure_alert" : {
                    "status": "update",
                    "sensor_type" : self.SENSOR_RESP_TYPE,
                    "alert_type": alert_type,
                    "resource_type" : self.RESOURCE_CATEGORY
                },
                "info" : details,
                "extended_info":ext
                }
            })

        return json_msg

    def _send_json_msg(self, alert_type, details, ext):
        """Transmit alert data to RealStorEnclMsgHandler to be processed
        and sent out
        """

        internal_json_msg = self._gen_json_msg(alert_type, details, ext)
        self.last_alert = internal_json_msg

        # Send the event to storage encl message handler to generate json message and send out
        self._write_internal_msgQ(RealStorEnclMsgHandler.name(), internal_json_msg)

    def _log_IEM(self, alert_type, details, ext):
        """Sends an IEM to logging msg handler"""
        json_data = self._gen_json_msg(alert_type, details, ext)

        # Send the event to storage encl message handler to generate json message
        # and send out
        internal_json_msg=json.dumps(
                {'actuator_request_type':
                    {'logging':
                        {'log_level': 'LOG_WARNING', 'log_type': 'IEM',
                          'log_msg': '{}'.format(json_data)}
                    }
                })

        # Send the event to logging msg handler to send IEM message to journald
        self._write_internal_msgQ(LoggingMsgHandler.name(), internal_json_msg)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RealStorDiskSensor, self).shutdown()
