#!/bin/env python3

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

import os
import errno
import socket

# using cortx package
from cortx.utils.process import SimpleProcess
from cortx.utils.security.cipher import Cipher
from cortx.utils.validator.v_bmc import BmcV
from cortx.utils.validator.v_controller import ControllerV
from cortx.utils.validator.v_network import NetworkV
from files.opt.seagate.sspl.setup.setup_error import SetupError
from framework.utils.utility import Utility
from framework.base.sspl_constants import PRVSNR_CONFIG_INDEX


class SSPLPrepare:
    """Setup and validate post network configuration."""

    name = "sspl_prepare"

    def __init__(self):
        """Initialize variables for prepare stage."""
        pass

    def validate(self):
        """Check below requirements.

        1. Validate input configs
        2. Validate BMC connectivity
        3. Validate storage controller connectivity
        4. Validate network interface availability
        """
        machine_id = Utility.get_machine_id()
        mgmt_interfaces = []
        data_private_interfaces = []
        data_public_interfaces = []

        # Validate input/provisioner configs
        node_type = Utility.get_config_value(PRVSNR_CONFIG_INDEX,
            "server_node>%s>type" % machine_id)
        cluster_id = Utility.get_config_value(PRVSNR_CONFIG_INDEX,
            "server_node>%s>cluster_id" % machine_id)
        if node_type.lower() not in ["virtual", "vm"]:
            bmc_ip = Utility.get_config_value(PRVSNR_CONFIG_INDEX,
                "server_node>%s>bmc>ip" % machine_id)
            bmc_user = Utility.get_config_value(PRVSNR_CONFIG_INDEX,
                "server_node>%s>bmc>user" % machine_id)
            secret = Utility.get_config_value(PRVSNR_CONFIG_INDEX,
                "server_node>%s>bmc>secret" % machine_id)
            key = Cipher.generate_key(cluster_id, "cluster")
            bmc_passwd = Cipher.decrypt(key, secret.encode("ascii")).decode()
            enclosure_id = Utility.get_config_value(PRVSNR_CONFIG_INDEX,
                "server_node>%s>storage>enclosure_id" % machine_id)
            primary_ip = Utility.get_config_value(PRVSNR_CONFIG_INDEX,
                "storage_enclosure>%s>storage>controller>primary>ip" % enclosure_id)
            secondary_ip = Utility.get_config_value(PRVSNR_CONFIG_INDEX,
                "storage_enclosure>%s>storage>controller>secondary>ip" % enclosure_id)
            cntrlr_user = Utility.get_config_value(PRVSNR_CONFIG_INDEX,
                "storage_enclosure>%s>storage>controller>user" % enclosure_id)
            cntrlr_passwd = Utility.get_config_value(PRVSNR_CONFIG_INDEX,
                "storage_enclosure>%s>storage>controller>password" % enclosure_id)
            data_private_interfaces = Utility.get_config_value(PRVSNR_CONFIG_INDEX,
                "server_node>%s>network>data>private_interfaces" % machine_id)
            data_public_interfaces = Utility.get_config_value(PRVSNR_CONFIG_INDEX,
                "server_node>%s>network>data>public_interfaces" % machine_id)
        mgmt_public_fqdn = Utility.get_config_value(PRVSNR_CONFIG_INDEX,
            "server_node>%s>network>management>public_fqdn" % machine_id)
        mgmt_interfaces = Utility.get_config_value(PRVSNR_CONFIG_INDEX,
            "server_node>%s>network>management>interfaces" % machine_id)
        data_private_fqdn = Utility.get_config_value(PRVSNR_CONFIG_INDEX,
            "server_node>%s>network>data>private_fqdn" % machine_id)
        data_public_fqdn = Utility.get_config_value(PRVSNR_CONFIG_INDEX,
            "server_node>%s>network>data>public_fqdn" % machine_id)

        # Validate BMC connectivity & storage controller accessibility
        if node_type.lower() not in ["virtual", "vm"]:
            NetworkV().validate("connectivity", [bmc_ip])
            c_validator = ControllerV()
            c_validator.validate("accessible", [primary_ip, cntrlr_user, cntrlr_passwd])
            c_validator.validate("accessible", [secondary_ip, cntrlr_user, cntrlr_passwd])

        # Validate network fqdn reachability
        NetworkV().validate("connectivity", [mgmt_public_fqdn,
            data_private_fqdn, data_public_fqdn])

        # Validate network interface availability
        for i_list in [mgmt_interfaces, data_private_interfaces, data_public_interfaces]:
            self.validate_nw_cable_connection(i_list)
            self.validate_nw_interfaces(i_list)

    def process(self):
        """Configure SSPL at prepare stage."""
        pass

    def validate_nw_cable_connection(self, interfaces):
        """Check network interface links are up.
        0 - Cable disconnected
        1 - Cable connected
        """
        if not isinstance(interfaces, list):
            raise SetupError(errno.EINVAL, "%s - validation failure. %s",
                self.name, "Expected list of interfaces. Received, %s." % interfaces)
        for interface in interfaces:
            cmd = "cat /sys/class/net/%s/carrier" % interface
            output, error, rc = SimpleProcess(cmd).run()
            output = output.decode().strip()
            if output == "0":
                raise SetupError(errno.EINVAL, "%s - validation failure. %s",
                    self.name, "Network interface cable is disconnected - %s." % interface)

    def validate_nw_interfaces(self, interfaces):
        """Check network intefaces are up."""
        if not isinstance(interfaces, list):
            raise SetupError(errno.EINVAL, "%s - validation failure. %s",
                self.name, "Expected list of interfaces. Received, %s." % interfaces)
        cmd = "ip --br a | awk '{print $1, $2}'"
        nws = [nw.strip() for nw in os.popen(cmd)]
        nw_status = {nw.split(" ")[0]: nw.split(" ")[1] for nw in nws}
        for interface, status in nw_status.items():
            if interface in interfaces and status in ["down", "DOWN"]:
                raise SetupError(errno.EINVAL, "%s - validation failure. %s",
                    self.name, "Network interface %s is down." % interface)
