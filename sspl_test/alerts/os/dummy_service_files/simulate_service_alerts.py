# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing, please email
# opensource@seagate.com or cortx-questions@seagate.com.

import os
import shutil
from cortx.utils.process import SimpleProcess
from cortx.utils.service import DbusServiceHandler

path = os.path.dirname(os.path.abspath(__file__))
service_name = "dummy_service.service"
service_file_path = f"{path}/{service_name}"
service_executable_code_src = f"{path}/dummy_service.py"
service_executable_code_des = "/var/cortx/sspl/test"
dbus_service = DbusServiceHandler()

def simulate_fault_alert():
    """Simulate fault for dummy service by deleting executable service file."""
    os.remove(f"{service_executable_code_des}/dummy_service.py")
    dbus_service.restart(service_name)

def restore_service_file():
    """Simulate fault resolved for dummy service by creating executable
        service file."""
    shutil.copy(service_executable_code_src, service_executable_code_des)
    # Make service file executable.
    cmd = f"chmod +x {service_executable_code_des}/dummy_service.py"
    execute_cmd(cmd)
    dbus_service.restart(service_name)

def cleanup():
    dbus_service.stop(service_name)
    dbus_service.disable(service_name)
    os.remove(f"{service_executable_code_des}/dummy_service.py")
    os.remove(f"/etc/systemd/system/{service_name}")
    execute_cmd("systemctl daemon-reload")

def execute_cmd(cmd):
    _, error, returncode = SimpleProcess(cmd).run()
    if returncode !=0:
        print("%s error occurred while executing cmd: %s" %(error, cmd))
