import sys
import os
import subprocess
import pwd

sys.path.insert(0, '/opt/seagate/cortx/sspl/low-level/')

from framework.base import sspl_constants 
import psutil


class Init:
    """Init Setup Interface"""
    name = "init"

    ### not needed if <ssu | gw | cmu> removed
    SSU_DEPENDENCY_RPMS = [
                "sg3_utils",
                "gemhpi",
                "pull_sea_logs",
                "python-hpi",
                "zabbix-agent-lib",
                "zabbix-api-gescheit",
                "zabbix-xrtx-lib",
                "python-openhpi-baselib",
                "zabbix-collector",
    ]

    SSU_REQUIRED_PROCESSES = [
                    "openhpid",
                    "dcs-collectord",
    ]
    ########################################

    VM_DEPENDENCY_RPMS = []

    def __init__(self, *args):
        self.args = args

    def usage(self):
        sys.stderr.write(
            f"{self.name} [check|create [-dp] [-r <ssu|gw|cmu|vm|cortx>]]\n"
            "create options:\n"
            "\t -dp Create configured datapath\n"
            "\t -r  Role to be configured on the current node\n" 
            )
        sys.exit(1)

    def _send_command(self, command : str, fail_on_error=True):
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        response, error = process.communicate()
        if error is not None and \
        len(error) > 0:
            print("command '%s' failed with error\n%s" % (command, error))
            if fail_on_error:
                sys.exit(1)
            else:
                return str(error)
        return str(response)

    def check_for_dep_rpms(self, rpm_list : list):
        # there is a way to do it using 'yum' pkg but curretly not working with python3, working on python2
        # inplemented using cmd command 'rpm -q pkgname' 
        for rpm in rpm_list:
            name = self._send_command('rpm -q ' + rpm)
            if 'not installed' in name:
                print(f"- Required rpm '{rpm}' not installed, exiting")
                sys.exit(1)
    
    def check_for_active_processes(self, process_list : list):
        running_pl = [procObj.name() for procObj in psutil.process_iter() if procObj.name() in process_list ]
        for process in process_list:
            if(process not in running_pl):
                print(f"- Required process '{process}' not running, exiting")
                sys.exit(1)

    def check_dependencies(self, role : str):
        ## function gets converted to single function call on removal of <ssu | cmu | gw> 
        ## and that function is also not doing anything since self.VM_DEPENDENCY_RPMS is empty

        # Check for dependency rpms and required processes active state based on role
        if role == "ssu":
            print(f"Checking for dependency rpms for role '{role}'")
            self.check_for_dep_rpms(self.SSU_DEPENDENCY_RPMS)
            print(f"Checking for required processes running state for role '{role}'")
            self.check_for_active_processes(self.SSU_REQUIRED_PROCESSES)
        elif role == "vm" or role == "gw" or role == "cmu":
            print(f"Checking for dependency rpms for role '{role}'")
            # No dependency currently. Keeping this section as it may be
            # needed in future.
            self.check_for_dep_rpms(self.VM_DEPENDENCY_RPMS)
            # No processes to check in vm env
        else:
            print(f"No rpm or process dependencies set, to check for supplied role {role}, skipping checks.\n")

    def get_uid(self, proc_name : str) -> int:
        uid = -1
        try :
            uid = pwd.getpwnam(proc_name).pw_uid
        except KeyError :
            print(f"No such User: {proc_name}")
        return uid

    def process(self):
        if not self.args:
            self.usage()

        i =0
        while i < len(self.args):
            if self.args[i] == '-dp':
                # Extract the data path
                sspldp = ''
                with open(sspl_constants.file_store_config_path, mode='rt') as confile:
                    for line in confile:
                        if line.find('data_path') != -1:
                            sspldp = line.split('=')[1]
                            break
                # Crete the directory and assign permissions
                try:
                    # what should be the permissions for this directory ??
                    os.makedirs(sspldp, mode=0o766, exist_ok=True)
                    sspl_ll_uid = self.get_uid('sspl-ll')
                    if sspl_ll_uid == -1:
                        sys.exit(1)
                    os.chown(sspldp, sspl_ll_uid, -1)
                    for root, dirs, files in os.walk(sspldp):
                        for item in dirs:
                            os.chown(os.path.join(root, item), sspl_ll_uid, -1)
                        for item in files:
                            os.chown(os.path.join(root, item), sspl_ll_uid, -1)
                except OSError as error:
                    print(error) 

            elif self.args[i] == '-r':
                i+=1
                if i>= len(self.args) or self.args[i] not in sspl_constants.roles:
                    self.usage()
                else:
                    self.role = self.args[i]
            else:
                self.usage()
            i+=1
        
        # Create /tmp/dcs/hpi if required. Not needed for '<product>' role
        if self.role != "cortx":
            try:
                os.makedirs('/tmp/dcs/hpi', mode=0o777, exist_ok=True)
                zabbix_uid = self.get_uid('zabbix')
                if zabbix_uid != -1:
                    os.chown('/tmp/dcs/hpi', zabbix_uid, -1)
            except OSError as error:
                print(error) 

        # Check for sspl required processes and misc dependencies like installation, etc based on 'role'
        if self.role : 
            self.check_dependencies(self.role)
        
        # Create mdadm.conf to set ACL on it.
        with open('/etc/mdadm.conf', 'a'):
            os.utime('/etc/mdadm.conf')

        # self._send_command('setfacl -m u:sspl-ll:rw /etc/mdadm.conf') 
        #  What should be the file permissions need here and are `setfacl` and below impl equivalent??
        os.chmod('/etc/mdadm.conf', mode=0o666)
        sspl_ll_uid = self.get_uid('sspl-ll')
        if sspl_ll_uid == -1:
            sys.exit(1)
        os.chown('/etc/mdadm.conf', sspl_ll_uid, -1)
        

if __name__ == "__main__":
    ic = Init('-r', 'ssu')
    ic.process()
