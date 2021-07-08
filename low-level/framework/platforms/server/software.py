#!/bin/python3

# CORTX Python common library.
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com

import os
import shlex

from cortx.utils.process import SimpleProcess
from cortx.utils.conf_store.error import ConfError
from cortx.utils.service.service_handler import DbusServiceHandler
from framework.platforms.server.error import BuildInfoError, ServiceError
from framework.utils.conf_utils import SSPL_CONF, Conf
from framework.base.sspl_constants import (CORTX_RELEASE_FACTORY_INFO,
    CONFIG_SPEC_TYPE, SYSTEMD_BUS, SERVICE_IFACE, UNIT_IFACE,
    DEFAULT_RECOMMENDATION)
from framework.utils.service_logging import logger
from dbus import PROPERTIES_IFACE, DBusException, Interface


class BuildInfo:
    """ Provides information for Cortx build, version, kernel etc. """

    name = "BuildInfo"
    _conf_loaded = False

    def __init__(self):
        """Initialize the class."""
        self.cortx_build_info_file_path = "%s://%s" % (
            CONFIG_SPEC_TYPE, CORTX_RELEASE_FACTORY_INFO)
        if not BuildInfo._conf_loaded:
            if os.path.exists(CORTX_RELEASE_FACTORY_INFO):
                Conf.load("cortx_build_info", self.cortx_build_info_file_path)
                BuildInfo._conf_loaded = True
            else:
                raise Exception("Build information file is unavailable")

    @staticmethod
    def get_attribute(attribute):
        """Get specific attribute from build info."""
        result = Conf.get("cortx_build_info", attribute)
        return result if result else "NA"


class Service:
    """ Provides methods to fetch information for systemd services """

    name = "Service"
    SERVICE_HANDLER = 'SERVICEMONITOR'
    SERVICE_LIST = 'monitored_services'

    def __init__(self):
        """Initialize the class."""
        self._bus, self._manager = DbusServiceHandler._get_systemd_interface()

    def get_external_service_list(self):
        """Get list of external services."""
        # TODO use solution supplied from RE for getting
        # list of external services.
        try:
            external_services = set(Conf.get(
                SSPL_CONF, f"{self.SERVICE_HANDLER}>{self.SERVICE_LIST}", []))
        except Exception as err:
            raise ServiceError(
                err.errno, ("Unable to get external service list due to Error: '%s, %s'"),
                err.strerror, err.filename)
        return external_services

    @staticmethod
    def get_cortx_service_list():
        """Get list of cortx services."""
        # TODO use solution supplied from HA for getting
        # list of cortx services or by parsing resource xml from PCS
        cortx_services = [
            "motr-free-space-monitor.service",
            "s3authserver.service",
            "s3backgroundproducer.service",
            "s3backgroundconsumer.service",
            "hare-hax.service",
            "haproxy.service",
            "sspl-ll.service",
            "kibana.service",
            "csm_agent.service",
            "csm_web.service",
            "event_analyzer.service",
        ]
        return cortx_services

    @staticmethod
    def get_service_info_from_rpm(service, prop):
        """
        Get specified service property from its corrosponding RPM.

        eg. (kafka.service,'LICENSE') -> 'Apache License, Version 2.0'
        """
        # TODO Include service execution path in systemd_path_list
        systemd_path_list = ["/usr/lib/systemd/system/",
                             "/etc/systemd/system/"]
        result = "NA"
        for path in systemd_path_list:
            # unit_file_path represents the path where
            # systemd service file resides
            # eg. kafka service -> /etc/systemd/system/kafka.service
            unit_file_path = path + service
            if os.path.isfile(unit_file_path):
                # this command will return the full name of RPM
                # which installs the service at given unit_file_path
                # eg. /etc/systemd/system/kafka.service -> kafka-2.13_2.7.0-el7.x86_64
                command = " ".join(["rpm", "-qf", unit_file_path])
                command = shlex.split(command)
                service_rpm, _, ret_code = SimpleProcess(command).run()
                if ret_code != 0:
                    return result
                try:
                    service_rpm = service_rpm.decode("utf-8")
                except AttributeError:
                    return result
                # this command will extract specified property from given RPM
                # eg. (kafka-2.13_2.7.0-el7.x86_64, 'LICENSE') -> 'Apache License, Version 2.0'
                command = " ".join(
                    ["rpm", "-q", "--queryformat", "%{"+prop+"}", service_rpm])
                command = shlex.split(command)
                result, _, ret_code = SimpleProcess(command).run()
                if ret_code != 0:
                    return result
                try:
                    # returned result should be in byte which need to be decoded
                    # eg. b'Apache License, Version 2.0' -> 'Apache License, Version 2.0'
                    result = result.decode("utf-8")
                except AttributeError:
                    return result
                break
        return result
    
    def get_systemd_service_info(self, log, service_name):
        """Get info of specified service using dbus API."""
        try:
            unit = self._bus.get_object(
                SYSTEMD_BUS, self._manager.LoadUnit(service_name))
            properties_iface = Interface(unit, dbus_interface=PROPERTIES_IFACE)
        except DBusException as err:
            logger.error(log.svc_log(
                f"Unable to initialize {service_name} due to {err}"))
            return None
        path_array = properties_iface.Get(SERVICE_IFACE, 'ExecStart')
        try:
            command_line_path = str(path_array[0][0])
        except IndexError as err:
            logger.error(log.svc_log(
                f"Unable to find {service_name} path due to {err}"))
            command_line_path = "NA"

        is_installed = True if command_line_path != "NA" or 'invalid' in properties_iface.Get(
            UNIT_IFACE, 'UnitFileState') else False
        uid = str(properties_iface.Get(UNIT_IFACE, 'Id'))
        if not is_installed:
            health_status = "NA"
            health_description = f"Software enabling {uid} is not installed"
            recommendation = "NA"
            specifics = [
                {
                    "service_name": uid,
                    "description": "NA",
                    "installed": str(is_installed).lower(),
                    "pid": "NA",
                    "state": "NA",
                    "substate": "NA",
                    "status": "NA",
                    "license": "NA",
                    "version": "NA",
                    "command_line_path": "NA"
                }
            ]
        else:
            service_license = "NA"
            version = "NA"
            service_description = str(
                properties_iface.Get(UNIT_IFACE, 'Description'))
            state = str(properties_iface.Get(UNIT_IFACE, 'ActiveState'))
            substate = str(properties_iface.Get(UNIT_IFACE, 'SubState'))
            service_status = 'enabled' if 'disabled' not in properties_iface.Get(
                UNIT_IFACE, 'UnitFileState') else 'disabled'
            pid = "NA" if state == "inactive" else str(
                properties_iface.Get(SERVICE_IFACE, 'ExecMainPID'))
            try:
                version = self.get_service_info_from_rpm(
                    uid, "VERSION")
            except ServiceError as err:
                logger.error(log.svc_log(
                    f"Unable to get service version due to {err}"))
            try:
                service_license = self.get_service_info_from_rpm(
                    uid, "LICENSE")
            except ServiceError as err:
                logger.error(log.svc_log(
                    f"Unable to get service license due to {err}"))

            specifics = [
                {
                    "service_name": uid,
                    "description": service_description,
                    "installed": str(is_installed).lower(),
                    "pid": pid,
                    "state": state,
                    "substate": substate,
                    "status": service_status,
                    "license": service_license,
                    "version": version,
                    "command_line_path": command_line_path
                }
            ]
            if service_status == 'enabled' and state == 'active' \
                    and substate == 'running':
                health_status = 'OK'
                health_description = f"{uid} is in good health"
                recommendation = "NA"
            else:
                health_status = state
                health_description = f"{uid} is not in good health"
                recommendation = DEFAULT_RECOMMENDATION

        return uid, health_status, health_description, recommendation, specifics
