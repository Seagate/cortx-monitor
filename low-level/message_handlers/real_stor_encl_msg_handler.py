# Copyright (c) 2001-2020 Seagate Technology LLC and/or its Affiliates
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
  Description:       Message Handler for processing enclosure level sensor data
  ****************************************************************************
"""


from cortx.sspl.framework.base.module_thread import ScheduledModuleThread
from cortx.sspl.framework.base.internal_msgQ import InternalMsgQ
from cortx.sspl.framework.utils.service_logging import logger
from cortx.sspl.json_msgs.messages.sensors.realstor_disk_data import RealStorDiskDataMsg
from cortx.sspl.json_msgs.messages.sensors.realstor_psu_data import RealStorPSUDataMsg
from cortx.sspl.json_msgs.messages.sensors.realstor_fan_data import RealStorFanDataMsg
from cortx.sspl.json_msgs.messages.sensors.realstor_controller_data import \
    RealStorControllerDataMsg
from cortx.sspl.json_msgs.messages.sensors.realstor_sideplane_expander_data import \
    RealStorSideplaneExpanderDataMsg
from cortx.sspl.json_msgs.messages.sensors.realstor_logical_volume_data import \
    RealStorLogicalVolumeDataMsg
from cortx.sspl.json_msgs.messages.sensors.realstor_encl_data_msg import RealStorEnclDataMsg
from cortx.sspl.framework.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor


class RealStorEnclMsgHandler(ScheduledModuleThread, InternalMsgQ):
    """Message Handler for processing real store sensor events and generating
        alerts in the RabbitMQ channel"""

    MODULE_NAME = "RealStorEnclMsgHandler"

    # TODO increase the priority
    PRIORITY = 2

    # Dependency list
    DEPENDENCIES = {
                    "plugins": ["RabbitMQegressProcessor"],
                    "rpms": []
    }

    @staticmethod
    def name():
        """ @return: name of the module."""
        return RealStorEnclMsgHandler.MODULE_NAME

    def __init__(self):
        super(RealStorEnclMsgHandler, self).__init__(self.MODULE_NAME,
                                                     self.PRIORITY)
        # Flag to indicate suspension of module
        self._suspended = False

    @staticmethod
    def dependencies():
        """Returns a list of plugins and RPMs this module requires
           to function.
        """
        return RealStorEnclMsgHandler.DEPENDENCIES

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread
        super(RealStorEnclMsgHandler, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RealStorEnclMsgHandler, self).initialize_msgQ(msgQlist)

        self._disk_sensor_message = None
        self._psu_sensor_message = None
        self._fan_module_sensor_message = None
        self._controller_sensor_message = None
        self._expander_sensor_message = None
        self._logical_volume_sensor_message = None
        self._enclosure_message = None

        # threading.Event object for waiting till msg is sent to rabbitmq
        self._event = None

        self._fru_func_dict = {
            "sideplane": self._generate_expander_alert,
            "fan": self._generate_fan_module_alert,
            "psu": self._generate_psu_alert,
            "controller": self._generate_controller_alert,
            "disk": self._generate_disk_alert,
            "logical_volume": self._generate_logical_volume_alert,
            "enclosure": self._generate_enclosure_alert
        }
        self._fru_type = {
            "sideplane": self._expander_sensor_message,
            "fan": self._fan_module_sensor_message,
            "psu": self._psu_sensor_message,
            "controller": self._controller_sensor_message,
            "disk": self._disk_sensor_message,
            "logical_volume": self._logical_volume_sensor_message,
            "enclosure": self._enclosure_message
        }

    def run(self):
        """Run the module periodically on its own thread."""
        self._log_debug("Start accepting requests")

        # Do not proceed if module is suspended
        if self._suspended == True:
            self._scheduler.enter(1, self._priority, self.run, ())
            return

        try:
            # Block on message queue until it contains an entry
            json_msg, self._event = self._read_my_msgQ()
            if json_msg is not None:
                self._process_msg(json_msg)

            # Keep processing until the message queue is empty
            while not self._is_my_msgQ_empty():
                json_msg, self._event = self._read_my_msgQ()
                if json_msg is not None:
                    self._process_msg(json_msg)

        except Exception as ae:
            # Log it and restart the whole process when a failure occurs
            logger.exception(f"RealStorEnclMsgHandler restarting: {ae}")

        self._scheduler.enter(1, self._priority, self.run, ())
        self._log_debug("Finished processing successfully")

    def _process_msg(self, json_msg):
        """Parses the incoming message and generate the desired data message"""
        self._log_debug(f"RealStorEnclMsgHandler, _process_msg, json_msg: {json_msg}")

        if json_msg.get("sensor_request_type").get("enclosure_alert") is not None:
            internal_sensor_request = json_msg.get("sensor_request_type").\
                                        get("enclosure_alert").get("status")
            if internal_sensor_request:
                resource_type = json_msg.get("sensor_request_type").\
                                get("enclosure_alert").get("info").get("resource_type")
                if ":" in resource_type:
                    sensor_type = resource_type.split(":")[2]
                else:
                    sensor_type = resource_type
                self._propagate_alert(json_msg, sensor_type)
            else:
                # serves the request coming from sspl CLI
                sensor_type = json_msg.get("sensor_request_type").\
                                get("enclosure_alert").get("info").\
                                    get("resource_type")
                if ":" in sensor_type:
                    sensor_type = sensor_type.split(":")[2]
                else:
                    sensor_type = sensor_type
                sensor_message_type = self._fru_type.get(sensor_type, "")

                # get the previously saved json message for the sensor type
                # and send the RabbitMQ Message
                if sensor_message_type:
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(),
                                              sensor_message_type, self._event)
                else:
                    self._log_debug(f"RealStorEnclMsgHandler, _process_msg, \
                        No past data found for {sensor_type} sensor type")
        else:
            logger.exception("RealStorEnclMsgHandler, _process_msg,\
                Not a valid sensor request format")

    def _propagate_alert(self, json_msg, sensor_type):
        """Extracts specific field from json message and propagates
           json message based on sensor type"""

        self._log_debug(f"RealStorEnclMsgHandler, _propagate_alert, json_msg {json_msg}")

        sensor_request = json_msg.get("sensor_request_type").get("enclosure_alert")
        host_name = sensor_request.get("host_id")
        alert_type = sensor_request.get("alert_type")
        alert_id = sensor_request.get("alert_id")
        severity = sensor_request.get("severity")
        info = sensor_request.get("info")
        specific_info = sensor_request.get("specific_info")
        self._log_debug(f"_processMsg, sensor_type: {sensor_type}")
        try:
            alert_func = self._fru_func_dict.get(sensor_type)
            alert_func(json_msg, host_name, alert_type, alert_id, severity, info,
                       specific_info, sensor_type)
        except TypeError:
            logger.error(f"RealStorEnclMsgHandler, _propagate_alert,\
                Not a valid sensor type: {sensor_type}")
        except Exception as e:
            logger.error(f"RealStorEnclMsgHandler, _propagate_alert,\
                error validating sensor_type: {sensor_type} {e}")

    def _generate_disk_alert(self, json_msg, host_name, alert_type, alert_id, severity,    \
                                       info, specific_info, sensor_type):
        """Parses the json message, also validates it and then send it to the
           RabbitMQ egress processor"""

        self._log_debug(f"RealStorEnclMsgHandler, _generate_disk_alert,\
            json_msg {json_msg}")

        real_stor_disk_data_msg = \
            RealStorDiskDataMsg(host_name, alert_type, alert_id, severity, info, specific_info)
        json_msg = real_stor_disk_data_msg.getJson()

        # save the json message in memory to serve sspl CLI sensor request
        self._disk_sensor_message = json_msg
        self._fru_type[sensor_type] = self._disk_sensor_message
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg, self._event)

    def _generate_psu_alert(self, json_msg, host_name, alert_type, alert_id,
                                             severity, info, specific_info, sensor_type):
        """Parses the json message, also validates it and then send it to the
           RabbitMQ egress processor"""

        self._log_debug(f"RealStorEnclMsgHandler, _generate_psu_alert,\
            json_msg {json_msg}")

        real_stor_psu_data_msg = \
            RealStorPSUDataMsg(host_name, alert_type, alert_id, severity, info, specific_info)
        json_msg = real_stor_psu_data_msg.getJson()

        # Saves the json message in memory to serve sspl CLI sensor request
        self._psu_sensor_message = json_msg
        self._fru_type[sensor_type] = self._psu_sensor_message
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg, self._event)

    def _generate_fan_module_alert(self, json_msg, host_name, alert_type, alert_id,
                                             severity, info, specific_info, sensor_type):
        """Parses the json message, also validates it and then send it to the
           RabbitMQ egress processor"""

        self._log_debug(f"RealStorEnclMsgHandler, _generate_fan_alert,\
            json_msg {json_msg}")

        real_stor_fan_data_msg = \
            RealStorFanDataMsg(host_name, alert_type, alert_id, severity, info, specific_info)
        json_msg = real_stor_fan_data_msg.getJson()

        # save the json message in memory to serve sspl CLI sensor request
        self._fan_module_sensor_message = json_msg
        self._fru_type[sensor_type] = \
            self._fan_module_sensor_message
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg, self._event)

    def _generate_controller_alert(self, json_msg, host_name, alert_type, alert_id,
                                       severity, info, specific_info, sensor_type):
        """Parses the json message, also validates it and then send it to the
           RabbitMQ egress processor"""

        self._log_debug(f"RealStorEnclMsgHandler, _generate_controller_alert,\
            json_msg {json_msg}")

        real_stor_controller_data_msg = \
            RealStorControllerDataMsg(host_name, alert_type, alert_id, severity, info,
                                      specific_info)
        json_msg = real_stor_controller_data_msg.getJson()

        # save the json message in memory to serve sspl CLI sensor request
        self._controller_sensor_message = json_msg
        self._fru_type[sensor_type] = \
            self._controller_sensor_message
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg, self._event)

    def _generate_expander_alert(self, json_msg, host_name, alert_type,
                                         alert_id, severity, info, specific_info, sensor_type):
        """Parses the json message, also validates it and then send it to the
           RabbitMQ egress processor"""

        self._log_debug(f"RealStorEnclMsgHandler, _generate_expander_alert,\
            json_msg {json_msg}")

        real_stor_expander_data_msg = \
            RealStorSideplaneExpanderDataMsg(host_name, alert_type, alert_id, severity, info,
                                             specific_info)
        json_msg = real_stor_expander_data_msg.getJson()

        # save the json message in memory to serve sspl CLI sensor request
        self._expander_sensor_message = json_msg
        self._fru_type[sensor_type] = \
            self._expander_sensor_message
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg, self._event)

    def _generate_logical_volume_alert(self, json_msg, host_name, alert_type, alert_id,
                                                   severity, info, specific_info, sensor_type):
        """Parses the json message, also validates it and then send it to the
           RabbitMQ egress processor"""

        self._log_debug(f"RealStorEnclMsgHandler, _generate_logical_volume_alert,\
            json_msg {json_msg}")

        real_stor_logical_volume_data_msg = \
            RealStorLogicalVolumeDataMsg(host_name, alert_type, alert_id, severity, info,
                                      specific_info)
        json_msg = real_stor_logical_volume_data_msg.getJson()

        # save the json message in memory to serve sspl CLI sensor request
        self._logical_volume_sensor_message = json_msg
        self._fru_type[sensor_type] = \
            self._logical_volume_sensor_message
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg, self._event)

    def _generate_enclosure_alert(self, json_msg, host_name, alert_type, alert_id,
                                            severity, info, specific_info, sensor_type):
        """Parses the json message, also validates it and then send it to the
            RabbitMQ egress processor"""

        self._log_debug(f"RealStorEnclMsgHandler, _generate_enclosure_alert,\
            json_msg {json_msg}")

        real_stor_encl_msg = RealStorEnclDataMsg(host_name, alert_type, alert_id, severity,
                                                info, specific_info)
        json_msg = real_stor_encl_msg.getJson()
        self._enclosure_message = json_msg
        self._fru_type[sensor_type] = self._enclosure_message
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg, self._event)

    def suspend(self):
        """Suspends the module thread. It should be non-blocking"""
        super(RealStorEnclMsgHandler, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(RealStorEnclMsgHandler, self).resume()
        self._suspended = False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""

        super(RealStorEnclMsgHandler, self).shutdown()
