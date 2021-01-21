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

import os
import errno
import shutil
import distutils.dir_util
from cortx.sspl.bin.sspl_constants import (REPLACEMENT_NODE_ENV_VAR_FILE, PRODUCT_NAME, SSPL_BASE_DIR,
    file_store_config_path, PRODUCT_BASE_DIR)
from cortx.utils.process import SimpleProcess
from cortx.utils.service import Service


class PostInstallError(Exception):
    """ Generic Exception with error code and output """

    def __init__(self, rc, message, *args):
        """Postinstallerror init."""
        self._rc = rc
        self._desc = message % (args)

    def __str__(self):
        """Postinstallerror str."""
        if self._rc == 0: return self._desc
        return "error(%d): %s" %(self._rc, self._desc)


class SSPLPostInstall:
    def __init__(self, args: list):
        """Ssplpostinstall init."""
        self.args = args
        self.name = "sspl_post_install"
        self._script_dir = os.path.dirname(os.path.abspath(__file__))
        self.RSYSLOG_CONF="/etc/rsyslog.d/0-iemfwd.conf"
        self.RSYSLOG_SSPL_CONF="/etc/rsyslog.d/1-ssplfwd.conf"
        self.PACEMAKER_INSTALLATION_PATH="/lib/ocf/resource.d/seagate/"

    def process(self):
        if not self.args or len({'-p', '-e', '-c'} & set(self.args)) == 0:
            raise PostInstallError(errno.EINVAL, f"Invalid Argument for {self.name}")

        PRODUCT = ""
        ENVIRONMENT = ""
        RMQ_CLUSTER = "true"
        i = 0
        while i < len(self.args):
            try:
                if self.args[i] == '-p':
                    PRODUCT = self.args[i+1]
                elif self.args[i] == '-e':
                    ENVIRONMENT = self.args[i+1]
                elif self.args[i] == '-c':
                    RMQ_CLUSTER = self.args[i+1]
            except (IndexError, ValueError):
                raise PostInstallError(errno.EINVAL, f"Invalid Argument for {self.name}")
            i+=1

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
                sspl_setup_consul = f"{self._script_dir}/sspl_setup_consul -e {ENVIRONMENT}"
                output, error, returncode = SimpleProcess(sspl_setup_consul).run()
                if returncode != 0:
                    raise PostInstallError(returncode, error, sspl_setup_consul)

        # Install packages which are not available in YUM repo, from PIP
        pip_cmd = f"python3 -m pip install -r {SSPL_BASE_DIR}/low-level/requirements.txt"
        output, error, returncode = SimpleProcess(pip_cmd).run()
        if returncode != 0:
            raise PostInstallError(returncode, error, pip_cmd)
        # Splitting current function into 2 functions to reduce the complexity of the code.
        self.install_files(PRODUCT, ENVIRONMENT, RMQ_CLUSTER)

    def install_files(self, PRODUCT, ENVIRONMENT, RMQ_CLUSTER):
        # NOTE: By default the sspl default conf file will not be copied.
        # The provisioner is supposed to copy the appropriate conf file based
        # on product/env and start SSPL with it.
        # TODO: Disable this default copy once the provisioners are ready.
        if not os.path.exists(file_store_config_path):
            shutil.copyfile(f"{SSPL_BASE_DIR}/conf/sspl.conf.{PRODUCT}", file_store_config_path)

        # For Dev environment
        if ENVIRONMENT == "DEV":
            shutil.copyfile(f"{SSPL_BASE_DIR}/conf/sspl.conf.{PRODUCT}", file_store_config_path)

        # Copy rsyslog configuration
        if not os.path.exists(self.RSYSLOG_CONF):
            shutil.copyfile(f"{SSPL_BASE_DIR}/low-level/files/{self.RSYSLOG_CONF}", self.RSYSLOG_CONF)

        if not os.path.exists(self.RSYSLOG_SSPL_CONF):
            shutil.copyfile(f"{SSPL_BASE_DIR}/low-level/files/{self.RSYSLOG_SSPL_CONF}", self.RSYSLOG_SSPL_CONF)

        # Create soft link for SINGLE product name service to existing LDR_R1, LDR_R2 service
        # Instead of keeping separate service file for SINGLE product with same content.
        currentProduct = f"{SSPL_BASE_DIR}/conf/sspl-ll.service.{PRODUCT}"
        if (PRODUCT == "SINGLE" and not os.path.exists(currentProduct)) or (PRODUCT == "DUAL" and not os.path.exists(currentProduct)):
            os.symlink(f"{SSPL_BASE_DIR}/conf/sspl-ll.service.{PRODUCT_NAME}", currentProduct)

        if PRODUCT == "CLUSTER" and not os.path.exists(currentProduct):
            os.symlink(f"{SSPL_BASE_DIR}/conf/sspl-ll.service.LDR_R2", currentProduct)

        # Copy sspl-ll.service file and enable service
        shutil.copyfile(currentProduct, "/etc/systemd/system/sspl-ll.service")
        Service('dbus').process('enable', 'sspl-ll.service')
        daemon_reload_cmd = "systemctl daemon-reload"
        output, error, returncode = SimpleProcess(daemon_reload_cmd).run()
        if returncode != 0:
            raise PostInstallError(returncode, error, daemon_reload_cmd)

        # Copy IEC mapping files
        os.makedirs(f"{PRODUCT_BASE_DIR}/iem/iec_mapping", exist_ok=True)
        distutils.dir_util.copy_tree(f"{SSPL_BASE_DIR}/low-level/files/iec_mapping/",
            f"{PRODUCT_BASE_DIR}/iem/iec_mapping")

        # Skip this step if sspl is being configured for node replacement scenario as sspl configurations are
        # already available in consul on the healthy node
        # Running script for fetching the config using salt and feeding values to consul
        # Onward LDR_R2, consul will be abstracted out and it won't exit as hard dependeny of SSPL
        if PRODUCT_NAME == "LDR_R1":
            if not os.path.exists(REPLACEMENT_NODE_ENV_VAR_FILE):
                config_from_salt = f"{self._script_dir}/sspl_fetch_config_from_salt.py {ENVIRONMENT} {PRODUCT_NAME}"
                output, error, returncode = SimpleProcess(config_from_salt).run()
                if returncode != 0:
                    raise PostInstallError(returncode, error, config_from_salt)
        else:
            load_sspl_config = f"{self._script_dir}/load_sspl_config.py -C {file_store_config_path}"
            output, error, returncode = SimpleProcess(load_sspl_config).run()
            if returncode != 0:
                raise PostInstallError(returncode, error, load_sspl_config)

        # Skip this step if sspl is being configured for node replacement scenario as rabbitmq cluster is
        # already configured on the healthy node
        # Configure rabbitmq
        if not os.path.exists(REPLACEMENT_NODE_ENV_VAR_FILE):
            if RMQ_CLUSTER == "true":
                rabbitmq_setup = f"{self._script_dir}/rabbitmq_setup"
                output, error, returncode = SimpleProcess(rabbitmq_setup).run()
                if returncode != 0:
                    raise PostInstallError(returncode, error, rabbitmq_setup)
