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

import shutil
import os
import pwd
import signal
import psutil
import time
import sys
from cortx.utils.process import SimpleProcess
# Add the top level directory to the sys.path to access classes
topdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.insert(0, topdir)
from framework.base.sspl_constants import DATA_PATH

SSPL_LL_D = "/opt/seagate/cortx/sspl/low-level/sspl_ll_d"
REPORT_PATH = f"{DATA_PATH}coverage/sspl_xml_coverage_report.xml"

PATCH_1 = """\
from coverage import Coverage
co = Coverage(
        data_file='%scoverage/.sspl_coverage_report',
        include="/opt/seagate/*",
        omit=['*/.local/*', '*/usr/*'],
        # config_file='%scoverage/.coveragerc',
        )\
"""%(DATA_PATH, DATA_PATH)

PATCH_2 = """\
        logger.info("Starting coverage report scope")
        co.start()\
"""

PATCH_3 = """\
def generate_cov_report(signal_number, frame):
    logger.info('Ending Coverage Scope')
    co.stop()
    logger.info('coverage object stopped.')
    co.save()
    logger.info('coverage info saved.')
    cov_per = co.xml_report(ignore_errors=True,
        outfile='%scoverage/sspl_xml_coverage_report.xml')
    logger.info(f'XML coverage report generated with coverage of {cov_per} percentage.')
    ## Enable below code to inable HTML report generation
    # html_cov_per = co.html_report(
    #                     directory='%scoverage/sspl_html_coverage',
    #                     ignore_errors=True,
    #                 )
    # logger.info(f'HTML coverage report geverated with coverage of {html_cov_per} percentage.')\
""" % (DATA_PATH, DATA_PATH)

PATCH_4 = """\
    signal.signal(signal.SIGUSR1, generate_cov_report)\
"""


def coverage_setup():
    """Creates required files for code coverage.

    Creates a temporary sspl_ll_d file and injects different patches of code
    to enable code coverage tracking. Also creates target directory for code
    coverage report and assigns permission to the directory.
    """
    print("Creating required files for coverage..")
    patch1_name = "initialize coverage obj for code coverage report generation"
    patch2_name = "start the code coverage scope"
    patch3_name = "stop coverage, save and generate code coverage report"
    patch4_name = "signal handler for SIGUSR1 to generate code coverage report"

    with open(SSPL_LL_D, 'r') as sspl_ll_d:
        sspl_ll_d_lines = sspl_ll_d.readlines()

    for i, line in enumerate(sspl_ll_d_lines):
        if patch1_name in line:
            for j,l in enumerate(PATCH_1.split('\n')):
                sspl_ll_d_lines.insert(i+j+1, l+'\n')
        elif patch2_name in line:
            for j,l in enumerate(PATCH_2.split('\n')):
                sspl_ll_d_lines.insert(i+j+1, l+'\n')
        elif patch3_name in line:
            for j,l in enumerate(PATCH_3.split('\n')):
                sspl_ll_d_lines.insert(i+j+1, l+'\n')
        elif patch4_name in line:
            for j,l in enumerate(PATCH_4.split('\n')):
                sspl_ll_d_lines.insert(i+j+1, l+'\n')

    shutil.move(SSPL_LL_D, f'{SSPL_LL_D}.bak')

    with open(SSPL_LL_D, 'x') as sspl_ll_d:
        for line in sspl_ll_d_lines:
            sspl_ll_d.write(line)

    print("Adding permission to files %s, %s"%(SSPL_LL_D, REPORT_PATH))
    uid =  pwd.getpwnam("sspl-ll").pw_uid
    os.chmod(SSPL_LL_D, 0o755)
    os.chown(SSPL_LL_D, uid, -1)

    os.makedirs(f'{DATA_PATH}coverage/', 0o755, exist_ok=True)
    os.chown(f'{DATA_PATH}coverage/', uid, -1)

    return 0

def coverage_reset():
    """Generates the code coverage report and resets the environment.

    Sends SIGUSR1 signal to sspl_ll_d to trigger code coverage report
    generation. Restores the original sspl_ll_d file.
    """
    print("Generating the coverage report..")
    pid = 0
    for proc in psutil.process_iter():
        if "sspl_ll_d" in proc.name():
            pid = proc.pid

    if pid:
        try:
            os.kill(pid, signal.SIGUSR1)
        except Exception as err:
            print(err)
    else:
        print("sspl-ll.service is not running.")

    time.sleep(5)

    if os.path.isfile(REPORT_PATH):
        modification_time = os.path.getmtime(REPORT_PATH)

        if (time.time() - modification_time) < 100:
            modification_time = \
                time.strftime('%Y-%m-%d %H:%M:%S',
                              time.localtime(modification_time))
            print("%s : The Code Coverage Report is saved at %s" %
                  (modification_time, REPORT_PATH))
        else:
            print("The Code Coverage Report generation failed.")
    else:
        print("%s file does not exists."%REPORT_PATH)

    print("Stoping the SSPL service..")
    cmd = 'systemctl stop sspl-ll.service'
    _, err, return_code = SimpleProcess(cmd).run()
    if return_code:
        print(err)
        return return_code

    if os.path.isfile(f'{SSPL_LL_D}.bak'):
        os.remove(SSPL_LL_D)
        shutil.move(f'{SSPL_LL_D}.bak', SSPL_LL_D)


def print_help():
    print('Error: Incorrect arguments to coverage_setup file.\n'
          'cmd : python3 coverage_setup.py [start/stop]\n'
          'Args => \n'
          '    start : Set-up the environment for code coverage.\n'
          '    stop : Reset the sspl environmet to normal.')


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print_help()
        sys.exit(100)
    if sys.argv[-1] == 'start':
        err_code = coverage_setup()
        sys.exit(err_code)
    elif sys.argv[-1] == 'stop':
        coverage_reset()
    else:
        print_help()
        sys.exit(100)
