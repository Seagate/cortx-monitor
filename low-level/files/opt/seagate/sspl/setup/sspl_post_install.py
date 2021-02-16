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
import shutil
import distutils.dir_util

# using cortx package
from cortx.utils.process import SimpleProcess
from cortx.utils.service import Service
from cortx.utils.conf_store import Conf
from cortx.sspl.lowlevel.files.opt.seagate.sspl.setup.error import SetupError
from cortx.sspl.bin.sspl_constants import (REPLACEMENT_NODE_ENV_VAR_FILE,
                                           SSPL_BASE_DIR,
                                           file_store_config_path,
                                           sspl_config_path,
                                           PRODUCT_BASE_DIR,
                                           GLOBAL_CONFIG)
from cortx.sspl.lowlevel.framework import sspl_rabbitmq_reinit


class SSPLPostInstall:
    """Prepare environment for SSPL service."""

    def __init__(self, args: str):
        """Ssplpostinstall init."""
        self.global_config = args.config[0]
        self.global_config_dump = args.config[-1]
        self.name = "sspl_post_install"
        self._script_dir = os.path.dirname(os.path.abspath(__file__))
        self.RSYSLOG_CONF="/etc/rsyslog.d/0-iemfwd.conf"
        self.RSYSLOG_SSPL_CONF="/etc/rsyslog.d/1-ssplfwd.conf"
        self.PACEMAKER_INSTALLATION_PATH="/lib/ocf/resource.d/seagate/"
        self.ENVIRONMENT = "PROD"

    def process(self):
        """Configure SSPL logs and service based on config."""
        PRODUCT_NAME = Conf.get(GLOBAL_CONFIG, 'release>product')

        # Copy and load product specific sspl config
        if not os.path.exists(file_store_config_path):
            shutil.copyfile("%s/conf/sspl.conf.%s.yaml" % (SSPL_BASE_DIR, PRODUCT_NAME),
                            file_store_config_path)

        # Global config copy path in sspl.conf will be referred by sspl-ll service later.
        Conf.load("sspl", sspl_config_path)
        Conf.set("sspl", "SYSTEM_INFORMATION>global_config_url", self.global_config)
        Conf.set("sspl", "SYSTEM_INFORMATION>global_config_dump_url", self.global_config_dump)
        Conf.save("sspl")

        environ = Conf.get("sspl", "SYSTEM_INFORMATION>environment")
        if environ == "DEV":
            self.ENVIRONMENT = environ

        # sspl_setup_consul script install consul in dev env and checks if consul process is running
        # on prod. For node replacement scenario consul will not be running on the new node. But,
        # there will be two instance of consul running on healthy node. When new node is configured
        # consul will be brought back on it. We are using VIP to connect to consul. So, if consul
        # is not running on new node, we dont need to error out. So, need to skip this step for
        # node replacement case
        # TODO: Need to avoid LDR in CORTX and check if we can use "CORTXr1"
        # Onward LR2, consul will be abstracted out and it won't exit as hard dependeny of SSPL
        if PRODUCT_NAME == "LDR_R1":
            # setup consul if not running already
            if not os.path.exists(REPLACEMENT_NODE_ENV_VAR_FILE):
                sspl_setup_consul = "%s/sspl_setup_consul -e %s" % (self._script_dir,
                                                                    self.ENVIRONMENT)
                output, error, returncode = SimpleProcess(sspl_setup_consul).run()
                if returncode != 0:
                    raise SetupError(returncode, error, sspl_setup_consul)

        # Install packages which are not available in YUM repo, from PIP
        pip_cmd = "python3 -m pip install -r %s/low-level/requirements.txt" % (SSPL_BASE_DIR)
        output, error, returncode = SimpleProcess(pip_cmd).run()
        if returncode != 0:
            raise SetupError(returncode, error, pip_cmd)
        # Splitting current function into 2 functions to reduce the complexity of the code.
        self.install_files(PRODUCT_NAME)

    def install_files(self, PRODUCT):
        """Configure required log files."""

        # Copy rsyslog configuration
        if not os.path.exists(self.RSYSLOG_CONF):
            shutil.copyfile("%s/low-level/files/%s" % (SSPL_BASE_DIR, self.RSYSLOG_CONF),
                            self.RSYSLOG_CONF)

        if not os.path.exists(self.RSYSLOG_SSPL_CONF):
            shutil.copyfile("%s/low-level/files/%s" % (SSPL_BASE_DIR, self.RSYSLOG_SSPL_CONF),
                            self.RSYSLOG_SSPL_CONF)

        # Create soft link for SINGLE product name service to existing LDR_R1, LR2 service
        # Instead of keeping separate service file for SINGLE product with same content.
        currentProduct = "%s/conf/sspl-ll.service.%s" % (SSPL_BASE_DIR, PRODUCT)
        if (PRODUCT == "SINGLE" and not os.path.exists(currentProduct)) or \
                (PRODUCT == "DUAL" and not os.path.exists(currentProduct)):
            os.symlink("%s/conf/sspl-ll.service.%s" % (SSPL_BASE_DIR, PRODUCT),
                       currentProduct)

        if PRODUCT == "CLUSTER" and not os.path.exists(currentProduct):
            os.symlink("%s/conf/sspl-ll.service.LR2" % (SSPL_BASE_DIR), currentProduct)

        # Copy sspl-ll.service file and enable service
        shutil.copyfile(currentProduct, "/etc/systemd/system/sspl-ll.service")
        Service('dbus').process('enable', 'sspl-ll.service')
        daemon_reload_cmd = "systemctl daemon-reload"
        output, error, returncode = SimpleProcess(daemon_reload_cmd).run()
        if returncode != 0:
            raise SetupError(returncode, error, daemon_reload_cmd)

        # Copy IEC mapping files
        os.makedirs("%s/iem/iec_mapping" % (PRODUCT_BASE_DIR), exist_ok=True)
        distutils.dir_util.copy_tree("%s/low-level/files/iec_mapping/" % (SSPL_BASE_DIR),
            "%s/iem/iec_mapping" % (PRODUCT_BASE_DIR))

        # Skip this step if sspl is being configured for node replacement scenario as sspl configurations are
        # already available in consul on the healthy node
        # Running script for fetching the config using salt and feeding values to consul
        # Onward LR2, consul will be abstracted out and it won't exit as hard dependeny of SSPL
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
                Service('dbus').process('start', 'rabbitmq-server.service')
                sspl_rabbitmq_reinit.main(PRODUCT)

