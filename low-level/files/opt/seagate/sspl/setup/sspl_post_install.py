#!/bin/env python3

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
import errno
import shutil
import distutils.dir_util

# using cortx package
from cortx.sspl.bin.error import SetupError
from cortx.sspl.bin.sspl_constants import (REPLACEMENT_NODE_ENV_VAR_FILE,
                                           SSPL_BASE_DIR,
                                           file_store_config_path,
                                           PRODUCT_BASE_DIR)
from cortx.sspl.lowlevel.framework import sspl_rabbitmq_reinit
from cortx.utils.process import SimpleProcess
from cortx.utils.service import Service
from cortx.utils.conf_store import Conf
from cortx.utils.conf_store.error import ConfError


class SSPLPostInstall:
    """Prepare environment for SSPL service"""

    def __init__(self, args: list):
        """Ssplpostinstall init."""
        self.args = args
        self.name = "sspl_post_install"
        self._script_dir = os.path.dirname(os.path.abspath(__file__))
        self.RSYSLOG_CONF="/etc/rsyslog.d/0-iemfwd.conf"
        self.RSYSLOG_SSPL_CONF="/etc/rsyslog.d/1-ssplfwd.conf"
        self.PACEMAKER_INSTALLATION_PATH="/lib/ocf/resource.d/seagate/"
        self.ENVIRONMENT = "PROD"

    def process(self):
        """Configure SSPL logs and service based on config"""

        PRODUCT_NAME = Conf.get('global_config', 'cluster>product')

        # Copy and load product specific sspl config
        if not os.path.exists(file_store_config_path):
            shutil.copyfile(f"{SSPL_BASE_DIR}/conf/sspl.conf.{PRODUCT_NAME}.yaml",
                            file_store_config_path)
        Conf.load("sspl", f"yaml://{file_store_config_path}")

        environ = Conf.get("sspl", "SYSTEM_INFORMATION>environment")
        if environ == "DEV":
            self.ENVIRONMENT = environ

        # sspl_setup_consul script install consul in dev env and checks if consul process is running
        # on prod. For node replacement scenario consul will not be running on the new node. But,
        # there will be two instance of consul running on healthy node. When new node is configured
        # consul will be brought back on it. We are using VIP to connect to consul. So, if consul
        # is not running on new node, we dont need to error out. So, need to skip this step for
        # node replacement case
        # Onward LDR_R2, consul will be abstracted out and it won't exit as hard dependeny of SSPL
        if PRODUCT_NAME == "LDR_R1":
            # setup consul if not running already
            if not os.path.exists(REPLACEMENT_NODE_ENV_VAR_FILE):
                sspl_setup_consul = "%s/sspl_setup_consul -e %s" % (self._script_dir,
                                                                    self.ENVIRONMENT)
                output, error, returncode = SimpleProcess(sspl_setup_consul).run()
                if returncode != 0:
                    raise SetupError(returncode, error, sspl_setup_consul)

        # Install packages which are not available in YUM repo, from PIP
        pip_cmd = f"python3 -m pip install -r {SSPL_BASE_DIR}/low-level/requirements.txt"
        output, error, returncode = SimpleProcess(pip_cmd).run()
        if returncode != 0:
            raise SetupError(returncode, error, pip_cmd)
        # Splitting current function into 2 functions to reduce the complexity of the code.
        self.install_files(PRODUCT_NAME)

    def install_files(self, PRODUCT):

        # Copy rsyslog configuration
        if not os.path.exists(self.RSYSLOG_CONF):
            shutil.copyfile(f"{SSPL_BASE_DIR}/low-level/files/{self.RSYSLOG_CONF}",
                            self.RSYSLOG_CONF)

        if not os.path.exists(self.RSYSLOG_SSPL_CONF):
            shutil.copyfile(f"{SSPL_BASE_DIR}/low-level/files/{self.RSYSLOG_SSPL_CONF}",
                            self.RSYSLOG_SSPL_CONF)

        # Create soft link for SINGLE product name service to existing LDR_R1, LDR_R2 service
        # Instead of keeping separate service file for SINGLE product with same content.
        currentProduct = f"{SSPL_BASE_DIR}/conf/sspl-ll.service.{PRODUCT}"
        if (PRODUCT == "SINGLE" and not os.path.exists(currentProduct)) or \
                (PRODUCT == "DUAL" and not os.path.exists(currentProduct)):
            os.symlink(f"{SSPL_BASE_DIR}/conf/sspl-ll.service.{PRODUCT}", currentProduct)

        if PRODUCT == "CLUSTER" and not os.path.exists(currentProduct):
            os.symlink(f"{SSPL_BASE_DIR}/conf/sspl-ll.service.LDR_R2", currentProduct)

        # Copy sspl-ll.service file and enable service
        shutil.copyfile(currentProduct, "/etc/systemd/system/sspl-ll.service")
        Service('dbus').process('enable', 'sspl-ll.service')
        daemon_reload_cmd = "systemctl daemon-reload"
        output, error, returncode = SimpleProcess(daemon_reload_cmd).run()
        if returncode != 0:
            raise SetupError(returncode, error, daemon_reload_cmd)

        # Copy IEC mapping files
        os.makedirs(f"{PRODUCT_BASE_DIR}/iem/iec_mapping", exist_ok=True)
        distutils.dir_util.copy_tree(f"{SSPL_BASE_DIR}/low-level/files/iec_mapping/",
            f"{PRODUCT_BASE_DIR}/iem/iec_mapping")

        # Skip this step if sspl is being configured for node replacement scenario as sspl configurations are
        # already available in consul on the healthy node
        # Running script for fetching the config using salt and feeding values to consul
        # Onward LDR_R2, consul will be abstracted out and it won't exit as hard dependeny of SSPL
        if PRODUCT == "LDR_R1":
            if not os.path.exists(REPLACEMENT_NODE_ENV_VAR_FILE):
                config_from_salt = "%s/sspl_fetch_config_from_salt.py %s %s" % (self._script_dir,
                                                                                self.ENVIRONMENT,
                                                                                PRODUCT)
                output, error, returncode = SimpleProcess(config_from_salt).run()
                if returncode != 0:
                    raise SetupError(returncode, error, config_from_salt)

        # Skip this step if sspl is being configured for node replacement scenario as rabbitmq cluster is
        # already configured on the healthy node
        # Configure rabbitmq
        if not os.path.exists(REPLACEMENT_NODE_ENV_VAR_FILE):
            setup_rmq = Conf.get("sspl", "RABBITMQCLUSTER>setup_rmq")
            if setup_rmq:
                Service('dbus').process('start', 'rabbitmq-server')
                sspl_rabbitmq_reinit.main(PRODUCT)

