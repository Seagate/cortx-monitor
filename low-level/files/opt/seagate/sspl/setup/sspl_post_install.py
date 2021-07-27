#!/usr/bin/python3.6

# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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
# please email opensource@seagate.com or cortx-questions@seagate.com.

###################################################################
# post_install script configures ryslog, sspl service and required
# site packages for SSPL. This is executed from sspl_setup script.
###################################################################

import os
import pwd
import errno
import shutil
import socket
import time
import distutils.dir_util

# using cortx package
from cortx.utils.conf_store import Conf
from cortx.utils.process import SimpleProcess
from cortx.utils.service.service_handler import ServiceError
from cortx.utils.validator.v_network import NetworkV
from cortx.utils.validator.v_pkg import PkgV
from cortx.utils.validator.v_service import ServiceV
from files.opt.seagate.sspl.setup.setup_error import SetupError
from files.opt.seagate.sspl.setup.setup_logger import logger
from framework.base import sspl_constants as consts
from framework.utils.utility import Utility
from framework.platforms.server.platform import Platform


class SSPLPostInstall:

    """Prepare environment for SSPL service."""

    name = "sspl_post_install"

    def __init__(self):
        """Initialize varibales for post install."""
        consts.SSPL_LOG_PATH = "/var/log/%s/sspl/" % consts.PRODUCT_FAMILY
        consts.SSPL_BUNDLE_PATH = "/var/%s/sspl/bundle/" % consts.PRODUCT_FAMILY
        self.state_file = "%s/state.txt" % consts.DATA_PATH

    def validate(self):
        """Check below requirements are met in setup.
        1. Check if given product is supported by SSPL
        2. Check if given setup is supported by SSPL
        3. Check if required pre-requisites softwares are installed.
        4. Validate BMC connectivity
        5. Validate storage controller connectivity
        """
        machine_id = Utility.get_machine_id()

        # Validate input/provisioner configs
        self.product = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "cortx>release>product")
        self.setup = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "cortx>release>setup")
        node_type = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
             "server_node>%s>type" % machine_id)
        if node_type.lower() not in ["vm", "virtual"]:
            bmc_ip = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
                "server_node>%s>bmc>ip" % machine_id)
        enclosure_id = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "server_node>%s>storage>enclosure_id" % machine_id)
        Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "storage_enclosure>%s>type" % enclosure_id)
        primary_ip = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "storage_enclosure>%s>controller>primary>ip" % enclosure_id)
        secondary_ip = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "storage_enclosure>%s>controller>secondary>ip" % enclosure_id)

        # Validate product support
        if self.product not in consts.enabled_products:
            msg = "Product '%s' is not in sspl supported product list: %s" % (
                self.product, consts.enabled_products)
            logger.error(msg)
            raise SetupError(errno.EINVAL, msg)

        # Validate setup support
        if self.setup not in consts.setups:
            msg = "Setup '%s' is not in sspl supported setup list: %s" % (
                self.setup, consts.setups)
            logger.error(msg)
            raise SetupError(errno.EINVAL, msg)

        # Validate required pip3s and rpms are installed
        self.validate_dependencies(self.setup)

        # Validate BMC & Storage controller IP reachability
        if node_type.lower() not in ["vm", "virtual"]:
            # cluster_id required for decrypting the secret is only available from
            # the prepare stage. However accessibility validation will be done in
            # prepare stage. So at this time, validating ip reachability is fine.
            NetworkV().validate("connectivity", [bmc_ip, primary_ip, secondary_ip])

    @staticmethod
    def validate_dependencies(setup):
        """Validate pre-requisites software packages."""
        pip3_3ps_packages_main = {
            "cryptography": "2.8",
            "jsonschema": "3.2.0",
            "pika": "1.1.0",
            "pyinotify": "0.9.6",
            "python-daemon": "2.2.4",
            "requests": "2.25.1",
            "zope.component": "4.6.2",
            "zope.event": "4.5.0",
            "zope.interface": "5.2.0"
            }
        rpm_3ps_packages = {
            "common": {
                "ipmitool": "1.8.18",
                "python36-dbus": "1.2.4",
                "python36-gobject": "3.22.0",
                "python36-paramiko": "2.1.1",
                "python36-psutil": "5.6.7",
                "shadow-utils": "4.6",
            },
            "el7": {
                "hdparm": "9.43",
                "lshw": "B.02.18",
                "python3": "3.6.8",
                "smartmontools": "7.0",
                "systemd-python36": "1.0.0",
                "udisks2": "2.8.4"
            },
            "el8": {
                "hdparm": "9.54",
                "lshw": "B.02.19.2",
                "python36": "3.6.8",
                "smartmontools": "7.1",
                "python3-systemd": "234",
                "udisks2": "2.9.0"
            }
        }
        ssu_dependency_rpms = [
            "sg3_utils",
            "gemhpi",
            "pull_sea_logs",
            "python-hpi",
            "zabbix-agent-lib",
            "zabbix-api-gescheit",
            "zabbix-xrtx-lib",
            "python-openhpi-baselib",
            "zabbix-collector"
            ]
        ssu_required_process = [
            "openhpid",
            "dcs-collectord"
            ]
        vm_dependency_rpms = []

        pkg_validator = PkgV()
        pkg_validator.validate_pip3_pkgs(host=socket.getfqdn(),
            pkgs=pip3_3ps_packages_main, skip_version_check=False)
        pkg_validator.validate_rpm_pkgs(
                host=socket.getfqdn(), pkgs=rpm_3ps_packages["common"],
                skip_version_check=False)
        os_release_version = Platform.get_os_info()['version_id']
        pkg_validator.validate_rpm_pkgs(
                host=socket.getfqdn(),
                pkgs=rpm_3ps_packages["el" + os_release_version[0]],
                skip_version_check=False)
        # Check for sspl required processes and misc dependencies if
        # setup/role is other than cortx
        if setup == "ssu":
            pkg_validator.validate("rpms", ssu_dependency_rpms)
            ServiceV().validate("isrunning", ssu_required_process)
        elif setup == "vm" or setup == "gw" or setup == "cmu":
            # No dependency currently. Keeping this section as it
            # may be needed in future.
            pkg_validator.validate("rpms", vm_dependency_rpms)
            # No processes to check in VM environment

    def process(self):
        """Create SSPL user and required config files."""
        # dbus module import is implicit in cortx utils. Keeping this
        # after dependency validation will enrich the use of
        # validate_dependencies() method.
        from cortx.utils.service import DbusServiceHandler
        self.dbus_service = DbusServiceHandler()

        # Create and load sspl config
        self.create_sspl_conf()
        Conf.load(consts.SSPL_CONFIG_INDEX, consts.sspl_config_path,
                  skip_reload=True)

        # Update sspl.conf with provisioner supplied input config copy
        Conf.set(
            consts.SSPL_CONFIG_INDEX, "SYSTEM_INFORMATION>global_config_copy_url",
            consts.global_config_path)
        Conf.save(consts.SSPL_CONFIG_INDEX)

        self.create_user()
        self.create_directories_and_ownership()
        self.configure_sspl_syslog()
        self.install_sspl_service_files()
        self.enable_sspl_service()

    def create_sspl_conf(self):
        """Install product specific sspl config."""
        # Copy and load product specific sspl config
        if not os.path.exists(consts.file_store_config_path):
            shutil.copyfile("%s/conf/sspl.conf.%s.yaml" % (consts.SSPL_BASE_DIR,
                self.product), consts.file_store_config_path)

    def create_user(self):
        """Add sspl-ll user and validate user creation."""
        os.system("/usr/sbin/useradd -r %s -s /sbin/nologin \
            -c 'User account to run the %s service'" % (consts.USER, consts.USER))
        usernames = [x[0] for x in pwd.getpwall()]
        if consts.USER not in usernames:
            msg = "User %s doesn't exit. Please add user." % (consts.USER)
            logger.error(msg)
            raise SetupError(errno.EINVAL, msg)
        # Add sspl-ll user to required groups and sudoers file etc.
        sspl_reinit = "%s/low-level/framework/sspl_reinit" % consts.SSPL_BASE_DIR
        _ , error, rc = SimpleProcess(sspl_reinit).run()
        if rc:
            msg = "%s failed for with error : %e" % (sspl_reinit, error)
            logger.error(msg)
            raise SetupError(rc, msg)

    def create_directories_and_ownership(self):
        """Create ras persistent cache directory and state file.

        Assign ownership recursively on the configured directory.
        The created state file will be used later by SSPL resourse agent(HA).
        """
        # Extract the data path
        sspldp = Utility.get_config_value(consts.SSPL_CONFIG_INDEX,
            "SYSTEM_INFORMATION>data_path")
        if not sspldp:
            raise SetupError(errno.EINVAL, "Data path not set in sspl.conf")
        sspl_uid = Utility.get_uid(consts.USER)
        sspl_gid = Utility.get_gid(consts.USER)
        if sspl_uid == -1 or sspl_gid == -1:
            msg = "No user found with name : %s" % (consts.USER)
            logger.error(msg)
            raise SetupError(errno.EINVAL, msg)
        # Create sspl data directory if not exists
        os.makedirs(sspldp, exist_ok=True)
        # Create state file under sspl data directory
        if not os.path.exists(self.state_file):
            file = open(self.state_file, "w")
            file.close()
        Utility.set_ownership_recursively(consts.SSPL_CONFIGURED_DIR,sspl_uid,sspl_gid)

        # Create SSPL log and bundle directories
        os.makedirs(consts.SSPL_LOG_PATH, exist_ok=True)
        os.makedirs(consts.SSPL_BUNDLE_PATH, exist_ok=True)
        # Create /tmp/dcs/hpi if required. Not required for '<product>' role
        if self.setup != "cortx":
            os.makedirs(consts.HPI_PATH, mode=0o777, exist_ok=True)
            zabbix_uid = Utility.get_uid("zabbix")
            if zabbix_uid != -1:
                os.chown(consts.HPI_PATH, zabbix_uid, -1)
        # Create mdadm.conf to set ACL on it.
        with open(consts.MDADM_PATH, 'a'):
            os.utime(consts.MDADM_PATH)
        os.chmod(consts.MDADM_PATH, mode=0o666)
        os.chown(consts.MDADM_PATH, sspl_uid, -1)

    def configure_sspl_syslog(self):
        """Configure log file path in rsyslog and update logrotate config file."""
        system_files_root = "%s/low-level/files" % consts.SSPL_BASE_DIR
        sspl_log_file_path = Utility.get_config_value(consts.SSPL_CONFIG_INDEX,
            "SYSTEM_INFORMATION>sspl_log_file_path")
        sspl_sb_log_file_path = sspl_log_file_path.replace("/sspl.log","/sspl_support_bundle.log")
        iem_log_file_path = Utility.get_config_value(consts.SSPL_CONFIG_INDEX,
            "IEMSENSOR>log_file_path")
        manifest_log_file_path = sspl_log_file_path.replace("/sspl.log","/manifest.log")

        # IEM configuration
        os.makedirs("%s/iem/iec_mapping" % consts.PRODUCT_BASE_DIR, exist_ok=True)
        distutils.dir_util.copy_tree("%s/iec_mapping/" % system_files_root,
            "%s/iem/iec_mapping" % consts.PRODUCT_BASE_DIR)
        if not os.path.exists(consts.RSYSLOG_IEM_CONF):
            shutil.copyfile("%s/%s" % (system_files_root, consts.RSYSLOG_IEM_CONF),
                consts.RSYSLOG_IEM_CONF)
        # Update log location as per sspl.conf
        Utility.replace_expr(consts.RSYSLOG_IEM_CONF,
            'File.*[=,"]', 'File="%s"' % iem_log_file_path)

        # SSPL rsys log configuration
        if not os.path.exists(consts.RSYSLOG_SSPL_CONF):
            shutil.copyfile("%s/%s" % (system_files_root, consts.RSYSLOG_SSPL_CONF),
                consts.RSYSLOG_SSPL_CONF)
        # Update log location as per sspl.conf
        Utility.replace_expr(consts.RSYSLOG_SSPL_CONF, 'File.*[=,"]',
            'File="%s"' % sspl_log_file_path)

        # Manifest Bundle log configuration
        if not os.path.exists(consts.RSYSLOG_MSB_CONF):
            shutil.copyfile("%s/%s" % (system_files_root, consts.RSYSLOG_MSB_CONF),
                consts.RSYSLOG_MSB_CONF)
        # Update log location as per sspl.conf
        Utility.replace_expr(consts.RSYSLOG_MSB_CONF, 'File.*[=,"]',
            'File="%s"' % manifest_log_file_path)

        # Support Bundle log configuration
        if not os.path.exists(consts.RSYSLOG_SB_CONF):
            shutil.copyfile("%s/%s" % (system_files_root, consts.RSYSLOG_SB_CONF),
                consts.RSYSLOG_SB_CONF)
        # Update log location as per sspl.conf
        Utility.replace_expr(consts.RSYSLOG_SB_CONF, 'File.*[=,"]',
            'File="%s"' % sspl_sb_log_file_path)

        # Configure logrotate
        # Create logrotate dir in case it's not present
        os.makedirs(consts.LOGROTATE_DIR, exist_ok=True)
        Utility.replace_expr("%s/etc/logrotate.d/iem_messages" % system_files_root,
            0, iem_log_file_path)
        Utility.replace_expr("%s/etc/logrotate.d/sspl_logs" % system_files_root,
            0, sspl_log_file_path)
        Utility.replace_expr("%s/etc/logrotate.d/sspl_sb_logs" % system_files_root,
            0, sspl_sb_log_file_path)
        shutil.copy2("%s/etc/logrotate.d/iem_messages" % system_files_root,
            consts.IEM_LOGROTATE_CONF)
        shutil.copy2("%s/etc/logrotate.d/sspl_logs" % system_files_root,
            consts.SSPL_LOGROTATE_CONF)
        shutil.copy2("%s/etc/logrotate.d/manifest_logs" % system_files_root,
            consts.MSB_LOGROTATE_CONF)
        shutil.copy2("%s/etc/logrotate.d/sspl_sb_logs" % system_files_root,
            consts.SB_LOGROTATE_CONF)

        # This rsyslog restart will happen after successful updation of rsyslog
        # conf file and before sspl starts. If at all this will be removed from
        # here, there will be a chance that SSPL intial logs will not be present in
        # "/var/log/<product>/sspl/sspl.log" file. So, initial logs needs to be collected from
        # "/var/log/messages"
        attempt = 0
        while attempt < 3:
            attempt += 1
            try:
                self.dbus_service.restart('rsyslog.service')
                break
            except ServiceError as err:
                if not attempt < 3:
                    logger.critical("Restarting rsyslog.service failed " \
                        "due to error, %s" % err)
                    raise
                logger.debug("Waiting for rsyslog service to become active..")
                time.sleep(2)

    def install_sspl_service_files(self):
        """Copy service file to systemd location based on product."""
        # Create soft link for SINGLE product name service to existing LDR_R1, LR2 service
        # Instead of keeping separate service file for SINGLE product with same content.
        currentProduct = "%s/conf/sspl-ll.service.%s" % (consts.SSPL_BASE_DIR,
                                                         self.product)
        if (self.product == "SINGLE" and not os.path.exists(currentProduct)) or \
                (self.product == "DUAL" and not os.path.exists(currentProduct)):
            os.symlink("%s/conf/sspl-ll.service.%s" % (consts.SSPL_BASE_DIR, self.product),
                       currentProduct)
        if self.product == "CLUSTER" and not os.path.exists(currentProduct):
            os.symlink("%s/conf/sspl-ll.service.LR2" % (consts.SSPL_BASE_DIR),
                       currentProduct)
        shutil.copyfile(currentProduct, "/etc/systemd/system/sspl-ll.service")

    def enable_sspl_service(self):
        """Enable sspl-ll service."""
        self.dbus_service.enable("sspl-ll.service")
        daemon_reload_cmd = "systemctl daemon-reload"
        output, error, rc = SimpleProcess(daemon_reload_cmd).run()
        if rc != 0:
            logger.error(f"Failed in enable sspl service. ERROR: {error}")
            raise SetupError(rc, error, daemon_reload_cmd)
