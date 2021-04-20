#! /usr/bin/python3

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

# NOTE : This script is written to replace start_sspl_coverage.sh and
#        stop_sspl_coverage.sh bash scripts with python script in future.
#        currently this file is not in use.

import shutil
import os
import pwd
import signal
import psutil
import time
from cortx.utils.process import SimpleProcess

file_path = "/opt/seagate/cortx/sspl/low-level"
report_path = "/var/cortx/sspl/coverage/sspl_xml_coverage_report.xml"

def coverage_setup():
    """Installs pip3 coverage package. Injects different patches code from
       coverage_code file to sspl_ll_d file, also creates target directory
       for code coverage report and assigns permission to the directory.
    """
    print("Installing coverage.py")
    _, _, return_code = SimpleProcess('python3 -m pip install coverage').run()
    if return_code:
        return return_code

    print("Creating required files for coverage..")
    patch1_name = "initialize coverage obj for code coverage report generation"
    patch1_start_ind = 0
    patch1_n_of_lines = 7

    patch2_name = "start the code coverage scope"
    patch2_start_ind = 7
    patch2_n_of_lines = 2

    patch3_name = "stop coverage, save and generate code coverage report"
    patch3_start_ind = 9
    patch3_n_of_lines = 15

    patch4_name = "signal handler for SIGUSR1 to generate code coverage report"
    patch4_start_ind = 24
    patch4_n_of_lines = 1

    if os.path.exists(f'{file_path}/sspl_ll_d_cov'):
        os.remove(f'{file_path}/sspl_ll_d_cov')

    with open('./coverage_code', 'r') as cov_code:
        cov_lines = cov_code.readlines()

    with open(f'{file_path}/sspl_ll_d', 'r') as sspl_ll_d:
        sspl_ll_d_lines = sspl_ll_d.readlines()

    for i, line in enumerate(sspl_ll_d_lines):
        if patch1_name in line:
            for j in range(patch1_n_of_lines):
                sspl_ll_d_lines.insert(i+j+1, cov_lines[patch1_start_ind+j])
        elif patch2_name in line:
            for j in range(patch2_n_of_lines):
                sspl_ll_d_lines.insert(i+j+1, cov_lines[patch2_start_ind+j])
        elif patch3_name in line:
            for j in range(patch3_n_of_lines):
                sspl_ll_d_lines.insert(i+j+1, cov_lines[patch3_start_ind+j])
        elif patch4_name in line:
            for j in range(patch4_n_of_lines):
                sspl_ll_d_lines.insert(i+j+1, cov_lines[patch4_start_ind+j])

    shutil.move(f'{file_path}/sspl_ll_d',
                f'{file_path}/sspl_ll_d.bak')

    with open(f'{file_path}/sspl_ll_d', 'x') as sspl_ll_d:
        for line in sspl_ll_d_lines:
            sspl_ll_d.write(line)

    print("coverage : adding permission to files %s, %s"%
            (f"{file_path}/sspl_ll_d", report_path))
    uid =  pwd.getpwnam("sspl-ll").pw_uid
    os.chmod(f"{file_path}/sspl_ll_d", 0o755)
    os.chown(f'{file_path}/sspl_ll_d', uid, -1)

    os.makedirs('/var/cortx/sspl/coverage/', 0o755, exist_ok=True)
    os.chown('/var/cortx/sspl/coverage/', uid, -1)

    return 0


def coverage_reset():
    """Send SIGUSR1 signal to sspl_ll_d to trigger code coverage report generation.
       Swap modified sspl_ll_d file with original one.
    """
    print("Generating the coverage report..")
    for proc in psutil.process_iter():
        if "sspl_ll_d" in proc.name():
            pid = proc.pid

    os.kill(pid, signal.SIGUSR1)
    time.sleep(5)

    modification_time = \
        os.path.getmtime(report_path)

    if (time.time() - modification_time) < 100:
        modification_time = time.strftime('%Y-%m-%d %H:%M:%S',
                                          time.localtime(modification_time))
        print("%s : The Code Coverage Report is saved at %s" %
              (modification_time, report_path))
    else:
        print("The Code Coverage Report is not generated.")

    os.remove(f'{file_path}/sspl_ll_d')
    shutil.move(f'{file_path}/sspl_ll_d.bak',
                f'{file_path}/sspl_ll_d')
