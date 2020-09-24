# CORTX-Monitor Quickstart Guide

This guide provides a step-by-step walkthrough for getting you CORTX-Monitor Server-ready.

- [1.0 Prerequisites](#10-Prerequisites)
- [1.2 Clone the cortx-monitor repository](#12-Clone-the-cortx-monitor-repository)
- [1.3 Build the cortx-monitor source code](#13-Build-the-cortx-monitor-source-code)
- [1.4 Run Tests](#14-Run-Tests)

## 1.0 Prerequisites

<details>
<summary>Click to expand!</summary>
<p>

1. You'll need to [Build and Test your VM Environment](https://github.com/Seagate/cortx/blob/main/doc/BUILD_ENVIRONMENT.md).
2. As a CORTX contributor you will need to refer, clone, contribute, and commit changes via the GitHub server. You can access the latest code via [Github](https://github.com/Seagate/cortx).
3. You'll need a valid GitHub Account. Follow the instructions to create an [SSH](https://github.com/Seagate/cortx/blob/Working_with_github/doc/SSH_Public_Key.rst) and [PAT](https://github.com/Seagate/cortx/blob/Working_with_github/doc/Tools.rst#personal-access-token-pat) access keys on your GitHub account.

:page_with_curl: **Note:** From this point onwards, you'll need to execute all steps logged in as a **Root User**.

4. We've assumed that `git` is preinstalled. If not then follow these steps to install [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git).
   * To check your Git Version, use the command: `$ git --version`
   
   :page_with_curl:**Note:** We recommended that you install Git Version 2.x.x.

5. Setup yum repos.
    
     1. Run the command:
            
            `$ curl https://raw.githubusercontent.com/Seagate/cortx-prvsnr/dev/cli/src/cortx-prereqs.sh?token=APA75GY34Y2F5DJSOKDCZAK7ITSZC -o cortx-prereqs.sh; chmod a+x cortx-prereqs.sh`
        
            1. For Cent-OS VMs, run the command:
        
                `$ sh cortx-prereqs.sh` 
        
            2. For Rhel VMs, run the command: 
        
                `$ sh cortx-prereqs.sh --disable-sub-mgr`

      2. Run the commands:

            ```shell
            
            $ BUILD_URL="http://cortx-storage.colo.seagate.com/releases/cortx/github/dev/rhel-7.7.1908/provisioner_last_successful"`
            $ yum-config-manager --add-repo  $BUILD_URL
            $ rpm --import  $BUILD_URL/RPM-GPG-KEY-Seagate
            ```

        :page_with_curl: **Notes:** 
        
      - If the https://raw.githubusercontent.com/Seagate/cortx-prvsnr/dev/cli/src/cortx-prereqs.sh?token=APA75GY34Y2F5DJSOKDCZAK7ITSZC link is not accessible, generate new one.

      - Visit https://github.com/Seagate/cortx-prvsnr/blob/dev/cli/src/cortx-prereqs.sh  and naviagte to **RAW** **>** **Copy URL** > **Use the URL for deployment**.

6. Follow the instructions [here to install dependencies](https://github.com/Seagate/cortx/blob/main/doc/InstallingDependencies.md)

    </p>
    </details>


## 1.2 Clone the cortx-monitor repository

1. Run the following commands to clone the cortx-monitor repository to your local VM:

    ```shell
    $ git clone --recursive https://github.com/Seagate/cortx-monitor.git -b main
    $ cd cortx-monitor
    ```

## 1.3 Build the cortx-monitor source code

:page_with_curl: **Notes:**

- cortx-monitor RPMs named as cortx-sspl.

- cortx-monitor service named as sspl-ll.

1. Before you build the RPM, you'll need to install the dependecies using:

    ```shell
    
    $ yum install rpm-build
    $ yum install autoconf automake libtool check-devel doxygen gcc graphviz openssl-devel python-pep8
    ```

    :page_with_curl: **Notes:**

    - If you faced following issue

    ```shell

    Error: Package: glibc-headers-2.17-307.el7.1.x86_64 (cortx_platform_base)
    Requires: kernel-headers >= 2.2.1
    ```

    Try this solution.

    ```shell

    sudo vim /etc/yum.conf
    comment  #exclude=kernel* (or remove the 'kernel*' part)
    ```

2. Build RPMs
    
   1. Switch to the directory where you've cloned cortx-monitor and run the command:
   
        `$ jenkins/build.sh`  
    
    :page_with_curl: **Notes:** 
    
    - It takes 2-3 minutes to generate RPMs.
    - Once the RPMs are successfully generated, you can view it from:
    
        `/root/rpmbuild/RPMS/noarch/` and,
     
        `/root/rpmbuild/RPMS/x86_64/`

    **Sample Output:**
    
    ```shell

    [local_host cortx-monitor]# ls -lrt /root/rpmbuild/RPMS/noarch/
    total 59056
    -rw-r--r-- 1 root root 34025516 Aug 18 07:26 cortx-sspl-1.0.0-1_git8907300.el7.noarch.rpm
    -rw-r--r-- 1 root root 16795340 Aug 18 07:27 cortx-sspl-cli-1.0.0-1_git8907300.el7.noarch.rpm
    -rw-r--r-- 1 root root  9643028 Aug 18 07:27 cortx-sspl-test-1.0.0-1_git8907300.el7.noarch.rpm


    [local_host cortx-monitor]# ls -lrt /root/rpmbuild/RPMS/x86_64/
    total 284
    -rw-r--r-- 1 root root  65968 Aug 18 07:23 systemd-python36-1.0.0-1_git8907300.el7.x86_64.rpm
    -rw-r--r-- 1 root root  60904 Aug 18 07:23 systemd-python36-debuginfo-1.0.0-1_git8907300.el7.x86_64.rpm
    -rw-r--r-- 1 root root   6552 Aug 18 07:27 cortx-libsspl_sec-1.0.0-1_git8907300.el7.x86_64.rpm
    -rw-r--r-- 1 root root  28448 Aug 18 07:27 cortx-libsspl_sec-debuginfo-1.0.0-1_git8907300.el7.x86_64.rpm
    -rw-r--r-- 1 root root   5760 Aug 18 07:27 cortx-libsspl_sec-method_none-1.0.0-1_git8907300.el7.x86_64.rpm
    -rw-r--r-- 1 root root   9592 Aug 18 07:27 cortx-libsspl_sec-method_pki-1.0.0-1_git8907300.el7.x86_64.rpm
    -rw-r--r-- 1 root root 101004 Aug 18 07:27 cortx-libsspl_sec-devel-1.0.0-1_git8907300.el7.x86_64.rpm
    ```

3. Install CORTX-Monitor RPMs

   You'll need to create a repository and copy all the required RPMs to it. Run the commands:

    ```shell
    
    $ mkdir MYRPMS
    $ cp -R /root/rpmbuild/RPMS/x86_64/cortx-libsspl_sec-* /root/rpmbuild/RPMS/noarch/cortx-sspl-* MYRPMS
    $ find MYRPMS -name \*.rpm -print0 | sudo xargs -0 yum install -y
    ```

4. To start the CORTX-Monitor service, run the commands:

    ```shell
    
    $ /opt/seagate/cortx/sspl/sspl_init
    $ systemctl start sspl-ll
    $ systemctl status sspl-ll
    ```
    You'll see the following service status:
    
     `Active: active (running)`


## 1.4 Run Tests
  
  1. Ensure that the following RPMs are installed and CORTX-Monitor service is Active. 
  
     - `cortx-sspl-1.0.0-XXXX.el7.noarch.rpm` and, 
     - `cortx-sspl-test-1.0.0-XXXX.el7.noarch.rpm` 
  
     Run the following commands:
     
     `$ rpm -qa | grep cortx-sspl`

      **Sample Output:**
       
      ```shell

        [local_host cortx-sspl]# rpm -qa | grep cortx-sspl
        cortx-sspl-1.0.0-1_git8907300.el7.noarch
        cortx-sspl-test-1.0.0-1_git8907300.el7.noarch
      ```
      `$ systemctl status sspl-ll`

  2. Run sanity test using:

      `$ /opt/seagate/cortx/sspl/bin/sspl_test sanity` or,
      `/opt/seagate/cortx/sspl/sspl_test/run_tests.sh`

      **Sample Output:**
    
 ```shell
    
    ******************************************************************************************
    TestSuite                                                    Status     Duration(secs)
    ******************************************************************************************
    alerts.node.test_node_disk_actuator                          Pass               10s
    alerts.realstor.test_real_stor_controller_sensor             Pass                4s
    alerts.realstor.test_real_stor_disk_sensor                   Pass                4s
    alerts.realstor.test_real_stor_fan_sensor                    Pass                4s
    alerts.realstor.test_real_stor_fan_actuator                  Pass                4s
    alerts.realstor.test_real_stor_psu_sensor                    Pass                4s
    alerts.realstor.test_real_stor_for_platform_sensor           Pass                6s
    alerts.realstor.test_real_stor_sideplane_expander_sensor     Pass                4s
    alerts.realstor.test_real_stor_disk_actuator                 Pass                4s
    alerts.realstor.test_real_stor_psu_actuator                  Pass                4s
    alerts.realstor.test_real_stor_controller_actuator           Pass                6s
    alerts.realstor.test_real_stor_sideplane_actuator            Pass                4s
    alerts.node.test_node_psu_actuator                           Pass                6s
    alerts.node.test_node_fan_actuator                           Pass                6s
    alerts.node.test_node_bmc_interface                          Pass               25s

    ****************************************************
    TestSuite:15 Tests:17 Passed:17 Failed:0 TimeTaken:108s
    ******************************************************
 ```

## You're All Set & You're Awesome!

We thank you for stopping by to check out the CORTX Community. We are fully dedicated to our mission to build open source technologies that help the world save unlimited data and solve challenging data problems. Join our mission to help reinvent a data-driven world.

### Contribute to CORTX-Monitor

Please refer to the [CORTX Contribution Guide](https://github.com/Seagate/cortx/blob/main/CONTRIBUTING.md) to contribute to the CORTX Project and join our movement to make data storage better, efficient, and more accessible.

### Reach Out to Us

Please refer to the [Support](SUPPORT.md) section to reach out to us with your questions, feedback, and issues.
