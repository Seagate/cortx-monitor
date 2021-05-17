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

import os
import sys
import time
import unittest
from functools import partial
from unittest.mock import Mock, patch

import dbus.exceptions

PROJECT_ROOT = "/".join(os.path.abspath(__file__).split("/")
                        [:-2]) + "/low-level"
sys.path.append(PROJECT_ROOT)

from sensors.impl.centos_7.service_monitor import (ServiceMonitor, Conf,
                                                   Service,
                                                   store, ActiveState,
                                                   InactiveState, SystemBus,
                                                   Interface, FailedState,
                                                   MonitoringDisabled,
                                                   EnabledState, DisabledState)


class TestServiceMonitor(unittest.TestCase):

    def setUp(self):
        self.mocked_conf_values = {
            "SERVICEMONITOR>monitored_services": ["spam.service"],
            "SERVICEMONITOR>thread_sleep": "1",
            "SERVICEMONITOR>polling_frequency": "5",
            "SERVICEMONITOR>threshold_inactive_time": "10"
        }
        self.mocked_properties_value = {
            "Id": "spam.service",
            "ActiveState": "N/A",
            "SubState": "N/A",
            "ExecMainPID": "N/A",
            "UnitFileState": "enabled"
        }

        Conf.get = Mock(side_effect=self.mocked_conf)
        Interface.Get = Mock(side_effect=self.mocked_properties)
        SystemBus.get_object = Mock()
        Service.dump_to_cache = Mock()
        Service.cache_exists = Mock(return_value=False)
        self.service_monitor = ServiceMonitor()
        self.service_monitor._write_internal_msgQ = Mock()
        self.service_monitor.is_running = Mock(return_value=True)
        time.sleep = Mock(side_effect=self.terminate_run)

    def mocked_conf(self, *args, **kwargs):
        key = args[1]
        return self.mocked_conf_values[key]

    def mocked_properties(self, *args, **kwargs):
        key = args[1]
        return self.mocked_properties_value[key]

    def service_monitor_run_iteration(self):
        self.service_monitor.is_running.return_value = True
        self.service_monitor.run()

    def terminate_run(self, *args, **kwargs):
        self.service_monitor.is_running.return_value = False


    @patch(
        'sensors.impl.centos_7.service_monitor.Service.is_nonactive_for_threshold_time',
        new=Mock(return_value=True))
    def test_fault_alert_if_service_is_inactive_at_start(self):
        self.mocked_properties_value["ActiveState"] = "inactive"
        self.service_monitor.initialize(Mock(), Mock(), Mock())
        self.service_monitor_run_iteration()
        fault_alert = self.assert_fault_is_raised()
        self.assertEqual(
            fault_alert["sensor_request_type"]["service_status_alert"][
                "specific_info"]["state"], "inactive")

    def assert_fault_is_raised(self):
        self.service_monitor._write_internal_msgQ.assert_called_once()
        fault_args = self.service_monitor._write_internal_msgQ.call_args
        _, fault_alert = fault_args[0]
        self.assertEqual(
            fault_alert["sensor_request_type"]["service_status_alert"][
                "severity"], "critical")
        self.assertEqual(
            fault_alert["sensor_request_type"]["service_status_alert"][
                "alert_type"], "fault")
        return fault_alert

    @patch(
        'sensors.impl.centos_7.service_monitor.Service.is_nonactive_for_threshold_time',
        new=Mock(return_value=True))
    def test_fault_alert_if_service_is_failed_at_start(self):
        self.fail_service_at_start()
        self.assert_failed_fault_is_raised()

    def assert_failed_fault_is_raised(self):
        fault_alert = self.assert_fault_is_raised()
        self.assertEqual(
            fault_alert["sensor_request_type"]["service_status_alert"][
                "specific_info"]["state"], "failed")

    def test_fault_alert_if_service_change_state_from_active_to_failed(self):
        self.service_active_at_start()
        self.mocked_properties_value["ActiveState"] = "failed"
        self.service_monitor_run_iteration()
        self.assert_failed_fault_is_raised()

    def test_fault_alert_if_service_change_state_from_active_to_inactive(
            self):
        self.mocked_properties_value["ActiveState"] = "active"
        self.service_monitor.initialize(Mock(), Mock(), Mock())
        self.service_monitor.services[
            "spam.service"].is_nonactive_for_threshold_time = Mock(
            return_value=True)
        self.service_monitor.process_events = Mock(
            side_effect=partial(self.service_monitor.services[
                                    "spam.service"].properties_changed_handler,
                                "", "", ""))
        self.mocked_properties_value["ActiveState"] = "inactive"
        self.service_monitor_run_iteration()
        fault_alert = self.assert_fault_is_raised()
        self.assertEqual(
            fault_alert["sensor_request_type"]["service_status_alert"][
                "specific_info"]["state"], "inactive")
        self.assertEqual(
            fault_alert["sensor_request_type"]["service_status_alert"][
                "specific_info"]["previous_state"], "active")

    def test_fault_resolved_if_service_change_state_from_failed_to_active(self):
        self.fail_service_at_start()
        self.assert_fault_is_raised()
        self.mocked_properties_value["ActiveState"] = "active"
        self.service_monitor.process_events = Mock(
            side_effect=partial(self.service_monitor.services[
                                    "spam.service"].properties_changed_handler,
                                "", "", ""))
        self.service_monitor_run_iteration()
        self.assertEqual(self.service_monitor._write_internal_msgQ.call_count,
                         2)
        resolved_args = self.service_monitor._write_internal_msgQ.call_args
        _, resolved_alert = resolved_args[0]
        self.assertEqual(
            resolved_alert["sensor_request_type"]["service_status_alert"][
                "severity"], "informational")
        self.assertEqual(
            resolved_alert["sensor_request_type"]["service_status_alert"][
                "alert_type"], "fault_resolved")
        self.assertEqual(
            resolved_alert["sensor_request_type"]["service_status_alert"][
                "specific_info"]["state"], "active")

    def fail_service_at_start(self):
        self.mocked_properties_value["ActiveState"] = "failed"
        self.service_monitor.initialize(Mock(), Mock(), Mock())
        self.service_monitor_run_iteration()

    def test_no_alert_if_state_changed_from_inactive_to_active_before_threshold(
            self):
        self.service_active_at_start()
        self.mocked_properties_value["ActiveState"] = "inactive"
        self.service_monitor_run_iteration()
        self.assertIn("spam.service", Service.non_active)
        self.mocked_properties_value["ActiveState"] = "active"
        self.service_monitor_run_iteration()
        self.assertNotIn("spam.service", Service.non_active)
        self.service_monitor._write_internal_msgQ.assert_not_called()

    def service_active_at_start(self):
        self.mocked_properties_value["ActiveState"] = "active"
        self.service_monitor.initialize(Mock(), Mock(), Mock())
        self.service_monitor.process_events = Mock(
            side_effect=partial(self.service_monitor.services[
                                    "spam.service"].properties_changed_handler,
                                "", "", ""))
        self.service_monitor_run_iteration()

    @patch(
        'sensors.impl.centos_7.service_monitor.Service.cache_exists',
        new=Mock(return_value=True))
    def test_fault_alert_if_service_is_inactive_in_cache(self):
        store.get = Mock(return_value={
            "service_state": "inactive",
            "service_monitor_state": InactiveState,
            "nonactive_enter_timestamp": time.time() - 999
        })
        self.service_monitor.initialize(Mock(), Mock(), Mock())
        self.assertIs(
            self.service_monitor.services["spam.service"]._service_state,
            InactiveState)
        self.service_monitor_run_iteration()
        self.service_monitor._write_internal_msgQ.assert_called_once()

    def test_no_alert_for_disabled_service(self):
        self.mocked_properties_value["UnitFileState"] = "disabled"
        self.mocked_properties_value["ActiveState"] = "failed"
        self.service_monitor.initialize(Mock(), Mock(), Mock())
        self.assertIs(self.service_monitor.services[
                          "spam.service"]._unit_state,
                      DisabledState)
        self.service_monitor_run_iteration()
        self.service_monitor._write_internal_msgQ.assert_not_called()

    def test_alert_for_enabled_service(self):
        # Service is disabled at start
        self.test_no_alert_for_disabled_service()
        # Enable service
        self.mocked_properties_value["UnitFileState"] = "enabled"
        self.service_monitor.unit_file_state_change_handler()
        self.assertIs(self.service_monitor.services[
                          "spam.service"]._unit_state, EnabledState)
        self.service_monitor_run_iteration()
        self.assert_fault_is_raised()

    @staticmethod
    def raise_dbus_exception(*args, **kwargs):
        signal = args[0]
        if signal == "PropertiesChanged":
            raise dbus.exceptions.DBusException

    def test_service_enters_into_monitoring_disabled_state_if_signal_reg_failed(
            self):
        Interface.connect_to_signal = Mock(
            side_effect=self.raise_dbus_exception)
        self.service_monitor.initialize(Mock(), Mock(), Mock())
        self.assertIs(self.service_monitor.services[
                          "spam.service"]._unit_state, MonitoringDisabled)
        self.service_monitor_run_iteration()
        self.assert_fault_is_raised()
        self.service_monitor_run_iteration()
        self.service_monitor_run_iteration()
        self.service_monitor._write_internal_msgQ.assert_called_once()
        self.mocked_properties_value["ActiveState"] = "active"
        Interface.connect_to_signal = Mock()
        self.service_monitor_run_iteration()
        self.assertIs(self.service_monitor.services[
                          "spam.service"]._unit_state, EnabledState)


    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()
