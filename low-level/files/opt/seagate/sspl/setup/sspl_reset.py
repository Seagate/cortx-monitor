import os
import shutil

from cortx.sspl.bin.sspl_constants import (PRODUCT_FAMILY,
 file_store_config_path, enabled_products)
from cortx.utils.process import SimpleProcess
from cortx.utils.service import Service

SSPL_CONFIGURED=f"/var/{PRODUCT_FAMILY}/sspl/sspl-configured"

class SSPLResetError(Exception):
    """ Generic Exception with error code and output """

    def __init__(self, rc, message, *args):
        self._rc = rc
        self._desc = message % (args)

    def __str__(self):
        if self._rc == 0: return self._desc
        return "error(%d): %s" %(self._rc, self._desc)


class SSPLResetCmd:

    def __init__(self, args: list):
        self.args = args
        self.name = "sspl_reset"
        self._config()

    def _config(self):
        if os.path.exists(file_store_config_path):
            with open(file_store_config_path, "r") as SSPL_CONF:
                for line in SSPL_CONF:
                    if 'data_path' in line:
                        self.SSPL_DATA_DIR=line.split("=")[1]
                    elif 'log_file_path' in line:
                        self.IEM_FILE_PATH=line.split("=")[1]
        else:
            self.SSPL_DATA_DIR=f"/var/{PRODUCT_FAMILY}/sspl/data"
            self.IEM_FILE_PATH=f"/var/{PRODUCT_FAMILY}/sspl/data/iem/iem_messages"
    
    def process(self):
        if not self.args:
            raise SSPLResetError(errno.EINVAL, "Invalid Argument for %s"% self.name)
        i=0
        while i < len(self.args):
            try:
                if self.args[i] == "hard":
                    HardCmd(self.args).process()
                elif self.args[i] == "soft":
                    SoftCmd(self.args).process()
            except (IndexError, ValueError):
                raise SSPLResetError(errno.EINVAL, "Invalid Argument for %s"% self.name)
            i+=1

    def del_file(self, filename):
        if os.path.exists(filename):
            os.remove(filename)


class HardCmd(SSPLResetCmd):
    """Hard reset Cmd"""
    name = "hard"
    user_present=False
    
    def __init__(self, args):
        super().__init__(args)

    def process(self):
        i = 0
        while i < len(self.args):
            try:
                if self.args[i] == '-p':
                    product = self.args[i+1]
                    break
            except (IndexError, ValueError):
                raise SSPLResetError(errno.EINVAL, "Invalid Argument for %s"% self.name)
            i+=1
        if product not in enabled_products:
            raise SSPLResetError(errno.EINVAL, "Invalid product for %s"% self.name)

        # stop sspl service
        Service('dbus').process('stop', 'sspl-ll.service')
        
        # Remove sspl_conf
        self.del_file(file_store_config_path)

        # Remove sspl-configured file
        self.del_file(SSPL_CONFIGURED)

        # Remove sspl data
        shutil.rmtree(self.SSPL_DATA_DIR, ignore_errors=True)

        # Remove sspl-ll user if preset
        CMD = "id -u sspl-ll"
        output, error, returncode = SimpleProcess(CMD).run()
        if returncode != 0:
            raise SSPLResetError(returncode, error, CMD)
        else:
            self.user_present=True
        
        if self.user_present:
            CMD="/usr/sbin/userdel sspl-ll"
            output, error, returncode = SimpleProcess(CMD).run()
            if returncode != 0:
                raise SSPLResetError(returncode, error, CMD)
            
        # Remove log directories
        shutil.rmtree(f"/var/log/{PRODUCT_FAMILY}/sspl", ignore_errors=True)
        shutil.rmtree(f"/var/log/{PRODUCT_FAMILY}/iem", ignore_errors=True)

        # Remove rsyslog config files
        self.del_file("/etc/rsyslog.d/0-iemfwd.conf")
        self.del_file("/etc/rsyslog.d/1-ssplfwd.conf")

        # Remove logrotate config files
        self.del_file("/etc/logrotate.d/iem_messages")
        self.del_file("/etc/logrotate.d/sspl_logs")

        # Remove SSPL configuration files
        shutil.rmtree("/etc/sspl-ll", ignore_errors=True)
        self.del_file("/etc/sspl.conf.bak")

class SoftCmd(SSPLResetCmd):
    """Soft reset Cmd"""
    name = "soft"
    

    def __init__(self, args):
        super().__init__(args)

    def process(self):
        # Remove .json files and truncate iem log file
        for root, dirs, files in os.walk("/var/cortx/sspl/data/"):
            for file in files:
                if file.endswith(".json"):
                    os.remove(os.path.join(root, file))
        if os.path.exists(self.IEM_FILE_PATH):
            with open(self.IEM_FILE_PATH, 'r+') as f:
                f.truncate()
