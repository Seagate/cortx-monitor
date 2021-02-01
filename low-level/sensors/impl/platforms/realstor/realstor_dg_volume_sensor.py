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
  Description:       Monitors Logical Volume data using RealStor API.
 ****************************************************************************
"""
import json
import os
import socket
import time
import uuid
from threading import Event

from zope.interface import implementer

from cortx.sspl.framework.base.internal_msgQ import InternalMsgQ
from cortx.sspl.framework.base.module_thread import SensorThread
from cortx.sspl.framework.platforms.realstor.realstor_enclosure import \
    singleton_realstorencl
from cortx.sspl.framework.utils.conf_utils import (POLLING_FREQUENCY_OVERRIDE,
    SSPL_CONF, Conf)
from cortx.sspl.framework.utils.service_logging import logger
from cortx.sspl.framework.utils.severity_reader import SeverityReader
from cortx.sspl.framework.utils.store_factory import store
# Modules that receive messages from this module
from cortx.sspl.message_handlers.real_stor_encl_msg_handler import RealStorEnclMsgHandler
from cortx.sspl.sensors.Ilogicalvolume import ILogicalVolumesensor


@implementer(ILogicalVolumesensor)
class RealStorLogicalVolumeSensor(SensorThread, InternalMsgQ):
    """Monitors Logical Volume data using RealStor API"""


    SENSOR_NAME = "RealStorLogicalVolumeSensor"
    SENSOR_RESP_TYPE = "enclosure_logical_volume_alert"
    RESOURCE_CATEGORY = "cortx"
    RESOURCE_TYPE_LVOL = "enclosure:cortx:logical_volume"
    RESOURCE_TYPE_DG = "enclosure:cortx:disk_group"

    PRIORITY = 1

    # Dependency list
    DEPENDENCIES = {
                    "plugins": ["RealStorEnclMsgHandler"],
                    "rpms": []
    }

    disk_groups_generic = ["object-name", "name", "size", "freespace", "storage-type", "pool",
         "pool-serial-number", "pool-percentage", "owner", "raidtype", "status", "create-date",
         "disk-description", "serial-number", "pool-sector-format", "health", "health-reason",
         "health-recommendation"]

    disk_groups_extended = ['blocksize', 'size-numeric', 'freespace-numeric', 'raw-size',
        'raw-size-numeric', 'storage-type-numeric', 'storage-tier', 'storage-tier-numeric',
        'total-pages', 'allocated-pages', 'available-pages', 'performance-rank', 'owner-numeric',
        'preferred-owner', 'preferred-owner-numeric', 'raidtype-numeric', 'diskcount', 'sparecount',
        'chunksize', 'status-numeric', 'lun', 'min-drive-size', 'min-drive-size-numeric',
        'create-date-numeric', 'cache-read-ahead', 'cache-read-ahead-numeric', 'cache-flush-period',
        'read-ahead-enabled', 'read-ahead-enabled-numeric', 'write-back-enabled',
        'write-back-enabled-numeric', 'job-running', 'current-job', 'current-job-numeric',
        'current-job-completion', 'num-array-partitions', 'largest-free-partition-space',
        'largest-free-partition-space-numeric', 'num-drives-per-low-level-array',
        'num-expansion-partitions', 'num-partition-segments', 'new-partition-lba',
        'new-partition-lba-numeric', 'array-drive-type', 'array-drive-type-numeric',
        'disk-description-numeric', 'is-job-auto-abortable', 'is-job-auto-abortable-numeric',
        'blocks', 'disk-dsd-enable-vdisk', 'disk-dsd-enable-vdisk-numeric', 'disk-dsd-delay-vdisk',
        'scrub-duration-goal', 'adapt-target-spare-capacity', 'adapt-target-spare-capacity-numeric',
        'adapt-actual-spare-capacity', 'adapt-actual-spare-capacity-numeric', 'adapt-critical-capacity',
        'adapt-critical-capacity-numeric', 'adapt-degraded-capacity', 'adapt-degraded-capacity-numeric',
        'adapt-linear-volume-boundary', 'pool-sector-format-numeric', 'health-numeric']

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
    # Disk Groups directory name
    DISK_GROUPS_DIR = "disk_groups"

    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return RealStorLogicalVolumeSensor.SENSOR_NAME

    @staticmethod
    def dependencies():
        """Returns a list of plugins and RPMs this module requires
           to function.
        """
        return RealStorLogicalVolumeSensor.DEPENDENCIES

    def __init__(self):
        super(RealStorLogicalVolumeSensor, self).__init__(
            self.SENSOR_NAME, self.PRIORITY)

        self._faulty_disk_group_file_path = None
        self._faulty_logical_volume_file_path = None

        self.rssencl = singleton_realstorencl

        # logical volumes persistent cache
        self._logical_volume_prcache = None
        # disk groups persistent cache
        self._disk_group_prcache = None

        # Holds Disk Groups with faults. Used for future reference.
        self._previously_faulty_disk_groups = {}
        # Holds Logical Volumes with faults. Used for future reference.
        self._previously_faulty_logical_volumes = {}

        self.pollfreq_logical_volume_sensor = \
            int(Conf.get(SSPL_CONF, f"{self.rssencl.CONF_REALSTORLOGICALVOLUMESENSOR}>{POLLING_FREQUENCY_OVERRIDE}",
                            0))

        if self.pollfreq_logical_volume_sensor == 0:
                self.pollfreq_logical_volume_sensor = self.rssencl.pollfreq

        # Flag to indicate suspension of module
        self._suspended = False

        self._event = Event()

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RealStorLogicalVolumeSensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RealStorLogicalVolumeSensor, self).initialize_msgQ(msgQlist)

        self._logical_volume_prcache = os.path.join(self.rssencl.frus,\
             self.LOGICAL_VOLUMES_DIR)
        self._disk_group_prcache = os.path.join(self.rssencl.frus,\
             self.DISK_GROUPS_DIR)

        # Persistence file location. This file stores faulty Logical Volume data
        self._faulty_logical_volume_file_path = os.path.join(
            self._logical_volume_prcache, "logical_volume_data.json")
        # Persistence file location. This file stores faulty Disk Group data
        self._faulty_disk_group_file_path = os.path.join(
            self._disk_group_prcache, "disk_group_data.json")

        # Load faulty Logical Volume data from file if available
        self._previously_faulty_logical_volumes = store.get(\
                                                  self._faulty_logical_volume_file_path)
        # Load faulty Disk Group data from file if available
        self._previously_faulty_disk_groups = store.get(\
                                                  self._faulty_disk_group_file_path)

        if self._previously_faulty_logical_volumes is None:
            self._previously_faulty_logical_volumes = {}
            store.put(self._previously_faulty_logical_volumes,\
                self._faulty_logical_volume_file_path)

        if self._previously_faulty_disk_groups is None:
            self._previously_faulty_disk_groups = {}
            store.put(self._previously_faulty_disk_groups,\
                self._faulty_disk_group_file_path)

        return True

    def read_data(self):
        """This method is part of interface. Currently it is not
        in use.
        """
        return {}

    def run(self):
        """Run the sensor on its own thread"""

        # Do not proceed if module is suspended
        if self._suspended == True:
            self._scheduler.enter(10, self._priority, self.run, ())
            return
        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        disk_groups = None
        logical_volumes = None

        try:
            disk_groups = self._get_disk_groups()

            if disk_groups:
                self._get_msgs_for_faulty_disk_groups(disk_groups)
                for disk_group in disk_groups:
                    pool_serial_number = disk_group["pool-serial-number"]
                    logical_volumes = self._get_logical_volumes(pool_serial_number)
                    if logical_volumes:
                        self._get_msgs_for_faulty_logical_volumes(logical_volumes, disk_group)

        except Exception as exception:
            logger.exception(exception)

        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()

        # Fire every 10 seconds to see if We have a faulty Logical Volume
        self._scheduler.enter(self.pollfreq_logical_volume_sensor,
                self._priority, self.run, ())

    def _get_disk_groups(self):
        """Receives list of Disk Groups from API.
           URL: http://<host>/api/show/disk-groups
        """
        url = self.rssencl.build_url(self.rssencl.URI_CLIAPI_SHOWDISKGROUPS)

        response = self.rssencl.ws_request(url, self.rssencl.ws.HTTP_GET)

        if not response:
            logger.warn(f"{self.rssencl.LDR_R1_ENCL}:: Disk Groups status unavailable as ws request {url} failed")
            return

        if response.status_code != self.rssencl.ws.HTTP_OK:
            if url.find(self.rssencl.ws.LOOPBACK) == -1:
                logger.error(f"{self.rssencl.LDR_R1_ENCL}:: http request {url} to get disk groups failed with  \
                     err {response.status_code}")
            return

        response_data = json.loads(response.text)
        disk_groups = response_data.get("disk-groups")
        return disk_groups

    def _get_logical_volumes(self, pool_serial_number):
        """Receives list of Logical Volumes from API.
           URL: http://<host>/api/show/volumes/pool/<pool_serial_number>
        """
        url = self.rssencl.build_url(self.rssencl.URI_CLIAPI_SHOWVOLUMES)

        url = f"{url}/pool/{pool_serial_number}"

        response = self.rssencl.ws_request(url, self.rssencl.ws.HTTP_GET)

        if not response:
            logger.warn(f"{self.rssencl.LDR_R1_ENCL}:: Logical Volume status unavailable as ws request {url}"
                " failed")
            return

        if response.status_code != self.rssencl.ws.HTTP_OK:
            logger.error(f"{self.rssencl.LDR_R1_ENCL}:: http request {url} to get logical volumes failed with \
                 err {response.status_code}")
            return

        response_data = json.loads(response.text)
        logical_volumes = response_data.get("volumes")
        return logical_volumes

    def _get_msgs_for_faulty_disk_groups(self, disk_groups, send_message=True):
        """Checks for health of disk groups and returns list of messages to be
           sent to handler if there are any.
        """
        faulty_disk_group_messages = []
        internal_json_msg = None
        disk_group_health = None
        serial_number = None
        alert_type = ""
        # Flag to indicate if there is a change in _previously_faulty_disk_groups
        state_changed = False

        if not disk_groups:
            return

        for disk_group in disk_groups:
            disk_group_health = disk_group["health"].lower()
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

            # Check for healthy case
            elif disk_group_health == self.rssencl.HEALTH_OK:
                # Status change from Fault ==> OK or Degraded ==> OK
                if serial_number in self._previously_faulty_disk_groups:
                    # Send message to handler
                    if send_message:
                        alert_type = self.rssencl.FRU_FAULT_RESOLVED
                    del self._previously_faulty_disk_groups[serial_number]
                    state_changed = True

            # Persist faulty Disk Group list to file only if something is changed
            if state_changed:
                # Generate the alert contents
                internal_json_msg = self._create_internal_msg_dg(alert_type, disk_group)
                faulty_disk_group_messages.append(internal_json_msg)
                # Send message to handler
                if send_message:
                    self._send_json_msg(internal_json_msg)
                # Wait till msg is sent to rabbitmq or added in consul for resending.
                # If timed out, do not update cache and revert in-memory cache.
                # So, in next iteration change can be detected
                if self._event.wait(self.rssencl.PERSISTENT_DATA_UPDATE_TIMEOUT):
                    store.put(self._previously_faulty_disk_groups,\
                        self._faulty_disk_group_file_path)
                else:
                    self._previously_faulty_disk_groups = store.get(self._faulty_disk_group_file_path)
                state_changed = False
            alert_type = ""
        return faulty_disk_group_messages

    def _get_msgs_for_faulty_logical_volumes(self, logical_volumes, disk_group, send_message=True):
        """Checks for health of logical volumes and returns list of messages to be
           sent to handler if there are any.
        """
        faulty_logical_volume_messages = []
        internal_json_msg = None
        logical_volume_health = None
        serial_number = None
        alert_type = ""
        # Flag to indicate if there is a change in _previously_faulty_logical_volumes
        state_changed = False

        if not logical_volumes:
            return

        for logical_volume in logical_volumes:
            logical_volume_health = logical_volume["health"].lower()
            serial_number = logical_volume["serial-number"]

            # Check for missing and fault case
            if logical_volume_health == self.rssencl.HEALTH_FAULT:
                # Status change from Degraded ==> Fault or OK ==> Fault
                if (serial_number in self._previously_faulty_logical_volumes and \
                        self._previously_faulty_logical_volumes[serial_number]['health']=="degraded") or \
                        (serial_number not in self._previously_faulty_logical_volumes):
                    alert_type = self.rssencl.FRU_FAULT
                    self._previously_faulty_logical_volumes[serial_number] = {
                        "health": logical_volume_health, "alert_type": alert_type}
                    state_changed = True

            # Check for degraded case
            elif logical_volume_health == self.rssencl.HEALTH_DEGRADED:
                # Status change from Fault ==> Degraded or OK ==> Degraded
                if (serial_number in self._previously_faulty_logical_volumes and \
                        self._previously_faulty_logical_volumes[serial_number]['health']=="fault") or \
                        (serial_number not in self._previously_faulty_logical_volumes):
                    alert_type = self.rssencl.FRU_FAULT
                    self._previously_faulty_logical_volumes[serial_number] = {
                        "health": logical_volume_health, "alert_type": alert_type}
                    state_changed = True

            # Check for healthy case
            elif logical_volume_health == self.rssencl.HEALTH_OK:
                # Status change from Fault ==> OK or Degraded ==> OK
                if serial_number in self._previously_faulty_logical_volumes:
                    # Send message to handler
                    alert_type = self.rssencl.FRU_FAULT_RESOLVED
                    del self._previously_faulty_logical_volumes[serial_number]
                    state_changed = True

            if state_changed:
                # Generate the alert contents
                internal_json_msg = self._create_internal_msg_lvol(
                    logical_volume, alert_type, disk_group)
                faulty_logical_volume_messages.append(internal_json_msg)
                # Send message to handler
                if send_message:
                    self._send_json_msg(internal_json_msg)
                # Persist faulty Logical Volume list to file only if something is changed
                # Wait till msg is sent to rabbitmq or added in consul for resending.
                # If timed out, do not update cache and revert in-memory cache.
                # So, in next iteration change can be detected
                if self._event.wait(self.rssencl.PERSISTENT_DATA_UPDATE_TIMEOUT):
                    store.put(self._previously_faulty_logical_volumes,\
                        self._faulty_logical_volume_file_path)
                else:
                    self._previously_faulty_logical_volumes = store.get(self._faulty_logical_volume_file_path)
                state_changed = False
            alert_type = ""

        return faulty_logical_volume_messages

    def _create_internal_msg_lvol(self, logical_volume_detail, alert_type, disk_group):
        """Forms a dictionary containing info about Logical Volumes to send to
           message handler.
        """
        if not logical_volume_detail:
            return {}

        generic_info = dict.fromkeys(self.volumes_generic, "NA")
        extended_info = dict.fromkeys(self.volumes_extended, "NA")
        disk_groups_info = dict.fromkeys(self.disk_groups_generic, "NA")

        severity_reader = SeverityReader()
        severity = severity_reader.map_severity(alert_type)
        epoch_time = str(int(time.time()))

        alert_id = self._get_alert_id(epoch_time)
        resource_id = logical_volume_detail.get("volume-name", "")
        host_name = socket.gethostname()

        for key, value in logical_volume_detail.items():
            if key in self.volumes_generic:
                generic_info.update({key : value})
            elif key in self.volumes_extended:
                extended_info.update({key : value})

        for key, value in disk_group.items():
            if key in self.disk_groups_generic:
                disk_groups_info.update({key : value})
        generic_info['disk-group'] = [disk_groups_info]
        generic_info.update(extended_info)

        info = {
                "site_id": self.rssencl.site_id,
                "cluster_id": self.rssencl.cluster_id,
                "rack_id": self.rssencl.rack_id,
                "node_id": self.rssencl.node_id,
                "resource_type": self.RESOURCE_TYPE_LVOL,
                "resource_id": resource_id,
                "event_time": epoch_time
                }

        internal_json_msg = json.dumps(
            {"sensor_request_type": {
                "enclosure_alert": {
                    "host_id": host_name,
                    "severity": severity,
                    "alert_id": alert_id,
                    "alert_type": alert_type,
                    "status": "update",
                    "info": info,
                    "specific_info": generic_info
                }
            }})
        return internal_json_msg

    def _create_internal_msg_dg(self, alert_type, disk_group_detail):
        """Forms a dictionary containing info about Disk Groups to send to
           message handler.
        """
        if not disk_group_detail:
            return {}

        generic_info = dict.fromkeys(self.disk_groups_generic, "NA")
        extended_info = dict.fromkeys(self.disk_groups_extended, "NA")

        severity_reader = SeverityReader()
        severity = severity_reader.map_severity(alert_type)
        epoch_time = str(int(time.time()))

        alert_id = self._get_alert_id(epoch_time)
        resource_id = disk_group_detail.get("name", "")
        host_name = socket.gethostname()

        for key, value in disk_group_detail.items():
            if key in self.disk_groups_generic:
                generic_info.update({key : value})
            elif key in self.disk_groups_extended:
                extended_info.update({key : value})

        generic_info.update(extended_info)

        info = {
                "site_id": self.rssencl.site_id,
                "cluster_id": self.rssencl.cluster_id,
                "rack_id": self.rssencl.rack_id,
                "node_id": self.rssencl.node_id,
                "resource_type": self.RESOURCE_TYPE_DG,
                "resource_id": resource_id,
                "event_time": epoch_time
                }

        internal_json_msg = json.dumps(
            {"sensor_request_type": {
                "enclosure_alert": {
                    "host_id": host_name,
                    "severity": severity,
                    "alert_id": alert_id,
                    "alert_type": alert_type,
                    "status": "update",
                    "info": info,
                    "specific_info": generic_info
                }
            }})
        return internal_json_msg

    def _get_alert_id(self, epoch_time):
        """Returns alert id which is a combination of
           epoch_time and salt value
        """
        salt = str(uuid.uuid4().hex)
        alert_id = epoch_time + salt
        return alert_id

    def _send_json_msg(self, json_msg):
        """Sends JSON message to Handler"""
        if not json_msg:
            return

        self._event.clear()
        # RAAL stands for - RAise ALert
        logger.info(f"RAAL: {json_msg}")
        self._write_internal_msgQ(RealStorEnclMsgHandler.name(), json_msg, self._event)

    def suspend(self):
        """Suspends the module thread. It should be non-blocking"""
        super(RealStorLogicalVolumeSensor, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(RealStorLogicalVolumeSensor, self).resume()
        self._suspended = False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RealStorLogicalVolumeSensor, self).shutdown()
