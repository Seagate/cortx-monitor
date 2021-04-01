#! /usr/bin/python3
import shutil
import os
import pwd
import signal
import psutil
import time

file_path = "/opt/seagate/cortx/sspl/low-level"
report_path = "/var/cortx/sspl/sspl_xml_coverage_report.xml"

def coverage_setup():
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
    
    os.chmod('/var/cortx/sspl/', 0o755)
    os.chown('/var/cortx/sspl/', uid, -1)


def coverage_reset():
    print("Generating the coverage report..")
    for proc in psutil.process_iter():
        if "sspl_ll_d" in proc.name():
            pid = proc.pid
    os.kill(pid, signal.SIGUSR1)
    time.sleep(5)
    modification_time = \
        os.path.getmtime(report_path)
    if(time.time() - modification_time < 100):
        modification_time = time.strftime('%Y-%m-%d %H:%M:%S', 
                                          time.localtime(modification_time))
        print("%s : The Code Coverage Report is saved at %s" %
              (modification_time, report_path))
    else:
        print("The Code Coverage Report is not generated.")

    os.remove(f'{file_path}/sspl_ll_d')
    shutil.move(f'{file_path}/sspl_ll_d.bak',
                f'{file_path}/sspl_ll_d')


if __name__ == "__main__":
    coverage_setup()
    coverage_reset()