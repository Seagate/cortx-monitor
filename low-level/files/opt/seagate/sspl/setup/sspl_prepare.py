#!/usr/bin/python3

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
import re
import errno
import socket

# using cortx package
from cortx.utils.conf_store import Conf
from cortx.utils.process import SimpleProcess
from cortx.utils.security.cipher import Cipher
from cortx.utils.validator.v_controller import ControllerV
from cortx.utils.validator.v_network import NetworkV
from files.opt.seagate.sspl.setup.setup_error import SetupError
from files.opt.seagate.sspl.setup.setup_logger import logger
from framework.utils.utility import Utility
from framework.base import sspl_constants as consts


class SSPLPrepare:

    """Setup and validate post network configuration."""

    name = "sspl_prepare"

    def __init__(self):
        """Initialize variables for prepare stage."""
        Conf.load(consts.SSPL_CONFIG_INDEX, consts.sspl_config_path)

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
        node_type = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "server_node>%s>type" % machine_id)
        Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "server_node>%s>cluster_id" % machine_id)
        if node_type.lower() not in ["virtual", "vm"]:
            bmc_ip = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
                "server_node>%s>bmc>ip" % machine_id)
            bmc_user = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
                "server_node>%s>bmc>user" % machine_id)
            bmc_secret = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
                "server_node>%s>bmc>secret" % machine_id)
            bmc_key = Cipher.generate_key(machine_id, consts.ServiceTypes.SERVER_NODE.value)
            bmc_passwd = Cipher.decrypt(bmc_key, bmc_secret.encode("utf-8")).decode("utf-8")
            data_private_interfaces = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
                "server_node>%s>network>data>private_interfaces" % machine_id)
            data_public_interfaces = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
                "server_node>%s>network>data>public_interfaces" % machine_id)
        mgmt_public_fqdn = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "server_node>%s>network>management>public_fqdn" % machine_id)
        mgmt_interfaces = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "server_node>%s>network>management>interfaces" % machine_id)
        data_private_fqdn = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "server_node>%s>network>data>private_fqdn" % machine_id)
        data_public_fqdn = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "server_node>%s>network>data>public_fqdn" % machine_id)
        enclosure_id = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "server_node>%s>storage>enclosure_id" % machine_id)
        primary_ip = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "storage_enclosure>%s>controller>primary>ip" % enclosure_id)
        secondary_ip = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "storage_enclosure>%s>controller>secondary>ip" % enclosure_id)
        cntrlr_user = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "storage_enclosure>%s>controller>user" % enclosure_id)
        cntrlr_secret = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "storage_enclosure>%s>controller>secret" % enclosure_id)
        cntrlr_key = Cipher.generate_key(enclosure_id,
            consts.ServiceTypes.STORAGE_ENCLOSURE.value)
        cntrlr_passwd = Cipher.decrypt(cntrlr_key,
            cntrlr_secret.encode("utf-8")).decode("utf-8")

        # Validate BMC connectivity & storage controller accessibility
        if node_type.lower() not in ["virtual", "vm"]:
            NetworkV().validate("connectivity", [bmc_ip, primary_ip, secondary_ip])
            # check BMC ip, user, password are valid
            self.test_bmc_is_accessible(bmc_ip, bmc_user, bmc_passwd)
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

    @staticmethod
    def test_bmc_is_accessible(bmc_ip, bmc_user, bmc_passwd):
        """Check if BMC is accessible through KCS or LAN."""
        channel_interface = Conf.get(
            consts.SSPL_CONFIG_INDEX, "BMC_INTERFACE>default", "system")

        if channel_interface == "system":
            # Check BMC is accessible through KCS
            cmd = "sudo ipmitool channel info"
            expected_channel = "KCS"
            channel_found = None
            channel_protocol = "Channel Protocol Type"
            res_op, res_err, res_rc = SimpleProcess(cmd).run()
            if res_rc == 0:
                res_op = res_op.decode()
                search_res = re.search(
                    r"%s[\s]+:[\s]+(\w+)(.*)" % channel_protocol, res_op)
                if search_res:
                    channel_found = search_res.groups()[0]
                if expected_channel != channel_found:
                    logger.critical(
                        "UNEXPECTED BMC CHANNEL TYPE FOUND. Expected: '%s' Found: '%s'" %(
                            expected_channel, channel_found))
            else:
                res_err = res_err.decode()
                kcs_errors = ("could not find inband device", "driver timeout")
                if not any(err for err in kcs_errors if err in res_err):
                    raise Exception("BMC is NOT accessible through KCS - ERROR: %s" % res_err)
        elif channel_interface == "lan":
            # Check BMC is accessible through LAN
            subcommand = "channel info"
            cmd = "sudo ipmitool -H %s -U %s -P %s -I lan %s" %(
                bmc_ip, bmc_user, bmc_passwd, subcommand)
            _, res_err, res_rc = SimpleProcess(cmd).run()
            if res_rc != 0:
                raise Exception("BMC is NOT accessible over lan - ERROR: %s" % res_err.decode())

    def process(self):
        """Configure SSPL at prepare stage."""
        # Update sspl.conf with provisioner supplied input config copy
        Conf.set(
            consts.SSPL_CONFIG_INDEX, "SYSTEM_INFORMATION>global_config_copy_url",
            consts.global_config_path)
        Conf.save(consts.SSPL_CONFIG_INDEX)

    def validate_nw_cable_connection(self, interfaces):
        """Check network interface links are up.

        0 - Cable disconnected
        1 - Cable connected
        """
        if not isinstance(interfaces, list):
            msg = "%s - validation failure. %s" % (self.name,
                "Expected list of interfaces. Received, %s." % interfaces)
            logger.error(msg)
            raise SetupError(errno.EINVAL, msg)
        for interface in interfaces:
            cmd = "cat /sys/class/net/%s/carrier" % interface
            output, error, rc = SimpleProcess(cmd).run()
            output = output.decode().strip()
            if output == "0":
                msg = "%s - validation failure. %s" % (self.name,
                    "Network interface cable is disconnected - %s." % interface)
                logger.error(msg)
                raise SetupError(errno.EINVAL, msg)

    def validate_nw_interfaces(self, interfaces):
        """Check network intefaces are up."""
        if not isinstance(interfaces, list):
            msg = "%s - validation failure. %s" % (self.name,
                "Expected list of interfaces. Received, %s." % interfaces)
            logger.error(msg)
            raise SetupError(errno.EINVAL, msg)
        cmd = "ip --br a | awk '{print $1, $2}'"
        nws = [nw.strip() for nw in os.popen(cmd)]
        nw_status = {nw.split(" ")[0]: nw.split(" ")[1] for nw in nws}
        for interface, status in nw_status.items():
            if interface in interfaces and status in ["down", "DOWN"]:
                msg = "%s - validation failure. %s" % (
                    self.name, "Network interface %s is down." % interface)
                logger.error(msg)
                raise SetupError(errno.EINVAL, msg)
