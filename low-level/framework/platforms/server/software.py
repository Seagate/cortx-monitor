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

from dbus import SystemBus, Interface
from cortx.utils.process import SimpleProcess

from cortx.utils.conf_store.error import ConfError
from cortx.utils.service.service_handler import DbusServiceHandler
from framework.platforms.server.error import BuildInfoError, ServiceError
from framework.utils.conf_utils import SSPL_CONF, Conf
from framework.base.sspl_constants import (CORTX_RELEASE_FACTORY_INFO,
                                           CONFIG_SPEC_TYPE)


class BuildInfo:
    """ Provides information for Cortx build, version, kernel etc. """

    name = "BuildInfo"

    def __init__(self):
        """Initialize the class."""
        self.cortx_build_info_file_path = "%s://%s" % (
            CONFIG_SPEC_TYPE, CORTX_RELEASE_FACTORY_INFO)
        if os.path.isfile(CORTX_RELEASE_FACTORY_INFO):
            Conf.load("cortx_build_info", self.cortx_build_info_file_path)

    @staticmethod
    def get_attribute(attribute):
        """Get specific attribute from build info."""
        result = "NA"
        try:
            result = Conf.get("cortx_build_info", attribute)
        except ConfError as err:
            raise BuildInfoError(
                err.errno, ("Unable to fetch '%s' due to Error: '%s, %s'"),
                attribute, err.strerror, err.filename)
        return result


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
