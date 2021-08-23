# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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
  Description:       Common set of Realstor enclosure management apis and utilities
 ********************************************************************************
"""
import json
import os
import time
import uuid

from zope.interface import implementer

from framework.base.module_thread import SensorThread
from framework.base.internal_msgQ import InternalMsgQ
from cortx.utils.log import Log as logger
from framework.utils.severity_reader import SeverityReader
from framework.platforms.realstor.realstor_enclosure import singleton_realstorencl
from framework.utils.store_factory import store
from framework.utils.os_utils import OSUtils

# Modules that receive messages from this module
from message_handlers.real_stor_encl_msg_handler import RealStorEnclMsgHandler

from sensors.Ienclosure import IEnclosure

@implementer(IEnclosure)
class RealStorEnclosureSensor(SensorThread, InternalMsgQ):
    """Monitors Enclosure"""

    # Dependency list
    DEPENDENCIES = {
                    "plugins": ["RealStorEnclMsgHandler"],
                    "rpms": []
                }

    SENSOR_NAME = "RealStorEnclosureSensor"
    SENSOR_RESP_TYPE = "enclosure_alert"
    RESOURCE_CATEGORY = "hw"
    RESOURCE_TYPE = "enclosure"

    ENCL_FAULT_RESOLVED_EVENTS = ["The network-port Ethernet link is down for controller A",\
                            "The network-port Ethernet link is down for controller B",\
                            "The Management Controller IP address changed",\
                            "The Management Controller booted up.",\
                            "Both controllers have shut down; no restart",\
                            "Storage Controller booted up (cold boot - power up).",\
                            "Management Controller configuration parameters were set"]

    PRIORITY = 1

    alert_type = None
    previous_alert_type = None
    fault_alert = False

    encl_status = None

    system_status = None

    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return RealStorEnclosureSensor.SENSOR_NAME

    @staticmethod
    def dependencies():
        """Returns a list of plugins and RPMs this module requires
        to function.
        """
        return RealStorEnclosureSensor.DEPENDENCIES

    def __init__(self):
        super(RealStorEnclosureSensor, self).__init__(self.SENSOR_NAME, self.PRIORITY)

        self.rssencl = singleton_realstorencl

        # Flag to indicate suspension of module
        self._suspended = False
        self.os_utils = OSUtils()

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RealStorEnclosureSensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RealStorEnclosureSensor, self).initialize_msgQ(msgQlist)

        self.ENCL_SENSOR_DATA_PATH = os.path.join(self.rssencl.encl_cache,
                                           'enclosure_data.json')
        # Get the stored previous alert info
        self.persistent_encl_data = store.get(self.ENCL_SENSOR_DATA_PATH)
        if self.persistent_encl_data:
            if self.persistent_encl_data['fault_alert'].lower() == "true":
                self.fault_alert = True
            else:
                self.fault_alert = False
            self.previous_alert_type = self.persistent_encl_data['previous_alert_type']
        else:
            self.persistent_encl_data = {
                'fault_alert' : str(self.fault_alert),
                'previous_alert_type' : str(self.previous_alert_type),
            }
            store.put(self.persistent_encl_data, self.ENCL_SENSOR_DATA_PATH)

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

        try:
            # Timeout counter for controller login failed and ws request failed
            mc_timeout_counter = self.rssencl.mc_timeout_counter
            # mc_timeout_counter==0, fault_alert==True & prev_alert_type!=FAULT_RESOLVED
            # all can be met True with a sspl restart & persistent cache, so ws_response
            # status finally decides whether to send FAULT_RESOLVED alert or not.
            ws_response_status = self.rssencl.ws_response_status

            if mc_timeout_counter > 10 and self.fault_alert is False:
                self.alert_type = self.rssencl.FRU_FAULT
                self.encl_status = "Storage Enclosure unreachable,"+\
                                    "Possible causes : Enclosure / Storage Controller /"+\
                                    "Management Controller rebooting,"+\
                                    "Network port blocked by firewall,"+\
                                    "Network outage or Power outage."

                self.fault_alert = True

            elif mc_timeout_counter == 0 and  ws_response_status == self.rssencl.ws.HTTP_OK \
                and self.previous_alert_type != self.rssencl.FRU_FAULT_RESOLVED \
                and self.fault_alert == True:

                # Check system status
                self.system_status = self.check_system_status()

                if self.system_status is not None:
                    self.alert_type = self.rssencl.FRU_FAULT_RESOLVED
                    enclosure_status = self.system_status[0:5]

                    for status in enclosure_status:
                        if status["severity"] == "INFORMATIONAL":
                            msg = status["message"]
                            for event in self.ENCL_FAULT_RESOLVED_EVENTS:
                                if event in msg:
                                    self.encl_status = event
                                    break

                    self.fault_alert = False

            if self.alert_type is not None:
                self.send_json_msg(self.alert_type, self.encl_status)
                self.alert_type = None
        except Exception as e:
            logger.exception(e)
        self._scheduler.enter(30, self._priority, self.run, ())

    def check_system_status(self):
        """Returns system staus using API /show/events"""

        url = self.rssencl.build_url(self.rssencl.URI_CLIAPI_SHOWEVENTS)
        # apply filter to fetch last 20 events
        url = url + " last 20"

        response = self.rssencl.ws_request(url, self.rssencl.ws.HTTP_GET)

        if not response:
            logger.warn("System status unavailable as ws request failed")
            return

        if response.status_code != self.rssencl.ws.HTTP_OK:
            if url.find(self.rssencl.ws.LOOPBACK) == -1:
                logger.error(f"{self.rssencl.LDR_R1_ENCL}:: http request {url} \
                                failed with http err {response.status_code}")
            return

        response_data = json.loads(response.text)
        enclosure_status = response_data["events"]

        return enclosure_status

    def send_json_msg(self, alert_type, encl_status):
        severity_reader = SeverityReader()
        severity = severity_reader.map_severity(alert_type)
        epoch_time = str(int(time.time()))
        alert_id = self._get_alert_id(epoch_time)
        fru = self.rssencl.is_storage_fru('enclosure')
        resource_id = "0"
        host_name = self.os_utils.get_fqdn()

        info = {
                "resource_type": self.RESOURCE_TYPE,
                "fru": fru,
                "resource_id": resource_id,
                "event_time": epoch_time,
                "description": encl_status
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
                    "specific_info": {
                        "event": encl_status
                        }
                    }
                }})

        self.previous_alert_type = alert_type
        self._write_internal_msgQ(RealStorEnclMsgHandler.name(), internal_json_msg)
        self.persistent_encl_data = {
                'fault_alert' : str(self.fault_alert),
                'previous_alert_type' : str(self.previous_alert_type),
            }
        store.put(self.persistent_encl_data, self.ENCL_SENSOR_DATA_PATH)

    def _get_alert_id(self, epoch_time):
        """Returns alert id which is a combination of
            epoch_time and salt value
        """
        salt = str(uuid.uuid4().hex)
        alert_id = epoch_time + salt
        return alert_id

    def suspend(self):
        """Suspend the module thread. It should be non-blocking"""
        super(RealStorEnclosureSensor, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(RealStorEnclosureSensor, self).resume()
        self._suspended = False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RealStorEnclosureSensor, self).shutdown()
