"""
 ****************************************************************************
 Filename:          realstor_logical_volume_sensor.py
 Description:       Monitors Logical Volume data using RealStor API.
 Creation Date:     09/09/2019
 Author:            Satish Darade

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import json
import re
import errno
import os

import requests
from zope.interface import implements

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.platforms.realstor.realstor_enclosure import singleton_realstorencl

# Modules that receive messages from this module
from message_handlers.real_stor_encl_msg_handler import RealStorEnclMsgHandler

from sensors.Ilogicalvolume import ILogicalVolumesensor


class RealStorLogicalVolumeSensor(ScheduledModuleThread, InternalMsgQ):
    """Monitors Logical Volume data using RealStor API"""

    implements(ILogicalVolumesensor)

    SENSOR_NAME = "RealStorLogicalVolumeSensor"
    SENSOR_RESP_TYPE = "enclosure_logical_volume_alert"
    RESOURCE_CATEGORY = "fru"

    PRIORITY = 1

    disk_groups_generic = ["object-name", "name", "size", "freespace", "storage-type", "pool",
         "pool-serial-number", "pool-percentage", "owner", "raidtype", "status", "create-date",
         "disk-description", "serial-number", "pool-sector-format", "health", "health-reason",
         "health-recommendation"]

    volumes_generic = ["volume-description", "blocks", "health", "size", "volume-name", "wwn",
         "storage-pool-name", "total-size", "volume-class", "allocated-size", "owner", "object-name",
         "raidtype", "health-reason", "progress", "blocksize", "serial-number", "virtual-disk-serial",
         "write-policy", "volume-type", "health-recommendation", "virtual-disk-name", "storage-type",
         "capabilities"]

    volumes_extended = ["cache-optimization", "container-serial", "cs-primary", "replication-set",
         "attributes", "preferred-owner", "volume-parent", "allowed-storage-tiers", "cs-copy-dest",
         "cs-copy-src", "container-name", "group-key", "snapshot-retention-priority", "pi-format",
         "reserved-size-in-pages", "cs-secondary", "volume-group", "health-numeric",
         "large-virtual-extents", "cs-replication-role", "durable-id", "threshold-percent-of-pool",
         "tier-affinity", "volume-qualifier", "snapshot", "snap-pool", "read-ahead-size",
         "zero-init-page-on-allocation", "allocate-reserved-pages-first"]

    # Logical Volumes directory name
    LOGICAL_VOLUMES_DIR = "logical_volumes"

    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return RealStorLogicalVolumeSensor.SENSOR_NAME

    def __init__(self):
        super(RealStorLogicalVolumeSensor, self).__init__(
            self.SENSOR_NAME, self.PRIORITY)

        self._faulty_disk_group_file_path = None

        self.rssencl = singleton_realstorencl

        # logical volumes persistent cache
        self._logical_volume_prcache = None

        # Holds Logical Volumes with faults. Used for future reference.
        self._previously_faulty_disk_groups = {}

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RealStorLogicalVolumeSensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RealStorLogicalVolumeSensor, self).initialize_msgQ(msgQlist)

        self._logical_volume_prcache = os.path.join(self.rssencl.frus,\
             self.LOGICAL_VOLUMES_DIR)

        # Create internal directory structure  if not present
        self.rssencl.check_prcache(self._logical_volume_prcache)

        # Persistence file location. This file stores faulty Logical Volume data
        self._faulty_disk_group_file_path = os.path.join(
            self._logical_volume_prcache, "logicalvolumedata.json")

        # Load faulty Logical Volume data from file if available
        self._previously_faulty_disk_groups = self.rssencl.jsondata.load(\
                                                  self._faulty_disk_group_file_path)

        if self._previously_faulty_disk_groups == None:
            self._previously_faulty_disk_groups = {}
            self.rssencl.jsondata.dump(self._previously_faulty_disk_groups,\
                self._faulty_disk_group_file_path)

    def read_data(self):
        """This method is part of interface. Currently it is not
        in use.
        """
        return {}

    def run(self):
        """Run the sensor on its own thread"""

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        disk_groups = None
        try:
            disk_groups = self._get_disk_groups()

            if disk_groups:
                self._get_msgs_for_faulty_disk_groups(disk_groups)

        except Exception as exception:
            logger.exception(exception)

        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()

        # Fire every 10 seconds to see if We have a faulty Logical Volume
        self._scheduler.enter(10, self._priority, self.run, ())

    def _get_disk_groups(self):
        """Receives list of Disk Groups from API.
           URL: http://<host>/api/show/disk-groups
        """
        url = self.rssencl.build_url(self.rssencl.URI_CLIAPI_SHOWDISKGROUPS)

        response = self.rssencl.ws_request(url, self.rssencl.ws.HTTP_GET)

        if not response:
            logger.warn("{0}:: Disk Groups status unavailable as ws request {1}"
                " failed".format(self.rssencl.EES_ENCL, url))
            return

        if response.status_code != self.rssencl.ws.HTTP_OK:
            if url.find(self.rssencl.ws.LOOPBACK) == -1:
                logger.error("{0}:: http request {1} to get disk groups failed with"
                    " err {2}".format(self.rssencl.EES_ENCL, url, response.status_code))
            return

        response_data = json.loads(response.text)
        disk_groups = response_data.get("disk-groups")
        return disk_groups

    def _get_logical_volumes(self, pool_serial_number):
        """Receives list of Logical Volumes from API.
           URL: http://<host>/api/show/volumes/pool/<pool_serial_number>
        """
        url = self.rssencl.build_url(self.rssencl.URI_CLIAPI_SHOWVOLUMES)

        url = url + "/pool/" + pool_serial_number

        response = self.rssencl.ws_request(url, self.rssencl.ws.HTTP_GET)

        if not response:
            logger.warn("{0}:: Logical Volume status unavailable as ws request {1}"
                " failed".format(self.rssencl.EES_ENCL, url))
            return

        if response.status_code != self.rssencl.ws.HTTP_OK:
            logger.error("{0}:: http request {1} to get logical volumes failed with"
                " err {2}" % self.rssencl.EES_ENCL, url, response.status_code)
            return

        response_data = json.loads(response.text)
        logical_volumes = response_data.get("volumes")
        return logical_volumes

    def _get_msgs_for_faulty_disk_groups(self, disk_groups, send_message=True):
        """Checks for health of logical volumes and returns list of messages to be
           sent to handler if there are any.
        """
        faulty_disk_group_messages = []
        internal_json_msg = None
        disk_group_health = None
        serial_number = None
        alert_type = ""
        logical_volumes = None
        # Flag to indicate if there is a change in _previously_faulty_disk_groups
        state_changed = False

        if not disk_groups:
            return

        for disk_group in disk_groups:
            disk_group_health = disk_group["health"].lower()
            pool_serial_number = disk_group["pool-serial-number"]
            serial_number = disk_group["serial-number"]
            # Check for missing and fault case
            if disk_group_health == self.rssencl.HEALTH_FAULT:
                # Status change from Degraded ==> Fault or OK ==> Fault
                if (serial_number in self._previously_faulty_disk_groups and \
                        self._previously_faulty_disk_groups[serial_number]['health']=="degraded") or \
                        (serial_number not in self._previously_faulty_disk_groups):
                    alert_type = self.rssencl.FRU_FAULT
                    self._previously_faulty_disk_groups[serial_number] = {
                        "health": disk_group_health, "alert_type": alert_type}
                    state_changed = True
                    logical_volumes = self._get_logical_volumes(pool_serial_number)
                    for logical_volume in logical_volumes:
                        internal_json_msg = self._create_internal_msg(
                            logical_volume, alert_type, disk_group)
                        faulty_disk_group_messages.append(internal_json_msg)
                        # Send message to handler
                        if send_message:
                            self._send_json_msg(internal_json_msg)
                            internal_json_msg = None
            # Check for fault case
            elif disk_group_health == self.rssencl.HEALTH_DEGRADED:
                # Status change from Fault ==> Degraded or OK ==> Degraded
                if (serial_number in self._previously_faulty_disk_groups and \
                        self._previously_faulty_disk_groups[serial_number]['health']=="fault") or \
                        (serial_number not in self._previously_faulty_disk_groups):
                    alert_type = self.rssencl.FRU_FAULT
                    self._previously_faulty_disk_groups[serial_number] = {
                        "health": disk_group_health, "alert_type": alert_type}
                    state_changed = True
                    logical_volumes = self._get_logical_volumes(pool_serial_number)
                    for logical_volume in logical_volumes:
                        internal_json_msg = self._create_internal_msg(
                            logical_volume, alert_type, disk_group)
                        faulty_disk_group_messages.append(internal_json_msg)
                        # Send message to handler
                        if send_message:
                            self._send_json_msg(internal_json_msg)
            # Check for healthy case
            elif disk_group_health == self.rssencl.HEALTH_OK:
                # Status change from Fault ==> OK or Degraded ==> OK
                if serial_number in self._previously_faulty_disk_groups:
                    # Send message to handler
                    if send_message:
                        alert_type = self.rssencl.FRU_FAULT_RESOLVED
                        logical_volumes = self._get_logical_volumes(pool_serial_number)
                        for logical_volume in logical_volumes:
                            internal_json_msg = self._create_internal_msg(
                                logical_volume, alert_type, disk_group)
                            faulty_disk_group_messages.append(internal_json_msg)
                            self._send_json_msg(internal_json_msg)
                    del self._previously_faulty_disk_groups[serial_number]
                    state_changed = True
            # Persist faulty Logical Volume list to file only if something is changed
            if state_changed:
                self.rssencl.jsondata.dump(self._previously_faulty_disk_groups,\
                    self._faulty_disk_group_file_path)
                state_changed = False
            alert_type = ""
        return faulty_disk_group_messages

    def _create_internal_msg(self, logical_volume_detail, alert_type, disk_group):
        """Forms a dictionary containing info about Logical Volumes to send to
           message handler.
        """
        if not logical_volume_detail:
            return {}

        info = dict.fromkeys(self.volumes_generic, "NA")
        extended_info = dict.fromkeys(self.volumes_extended, "NA")
        disk_groups_info = dict.fromkeys(self.disk_groups_generic, "NA")

        for key, value in logical_volume_detail.items():
            if key in self.volumes_generic:
                info.update({key : value})
            elif key in self.volumes_extended:
                extended_info.update({key : value})

        for key, value in disk_group.items():
            if key in self.disk_groups_generic:
                disk_groups_info.update({key : value})
        info['disk-group'] = [disk_groups_info]

        internal_json_msg = json.dumps(
            {"sensor_request_type": {
                    "enclosure_alert": {
                        "sensor_type" : self.SENSOR_RESP_TYPE,
                        "resource_type": self.RESOURCE_CATEGORY,
                        "alert_type": alert_type,
                        "status": "update"
                    },
                    "info": info,
                    "extended_info": extended_info
            }})
        return internal_json_msg

    def _send_json_msg(self, json_msg):
        """Sends JSON message to Handler"""
        if not json_msg:
            return
        self._write_internal_msgQ(RealStorEnclMsgHandler.name(), json_msg)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RealStorLogicalVolumeSensor, self).shutdown()
