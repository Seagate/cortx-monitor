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
5. You'll need docker to build third-party dependency RPMs. Please follow guidelines from [Docker](https://docs.docker.com/engine/install/centos/)
   Quick steps are given below.
   ```shell
   sudo yum remove docker \
                  docker-client \
                  docker-client-latest \
                  docker-common \
                  docker-latest \
                  docker-latest-logrotate \
                  docker-logrotate \
                  docker-engine
   yum install -y yum-utils
   yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
   yum install docker-ce docker-ce-cli containerd.io
   ```

</p>
</details>


## 1.2 Clone the cortx-monitor repository

1. Run the following commands to clone the cortx-monitor repository to your local VM:

    ```shell
    $ cd ~ && git clone https://github.com/Seagate/cortx --recursive --depth=1
    ```

## 1.3 Build the cortx-monitor source code

:page_with_curl: **Notes:**

- cortx-monitor RPMs named as cortx-sspl.

- cortx-monitor service named as sspl-ll.

1. Before you build the RPM, you'll need to install the dependencies using:

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

   1. Start Docker
      ```sh
      sudo systemctl start docker
      sudo systemctl status docker
      ```

   2. Checkout the main branch
   
        `docker run --rm -v /root/cortx:/cortx-workspace ghcr.io/seagate/cortx-build:centos-7.8.2003 make checkout BRANCH=main`  
    
    :page_with_curl: **Notes:** 
    
    - If you get below error it may be because that your git version may be more thatn 2.x. Cortx requires 1.8.3.1. In that case
      if go to `~/cortx/cortx-monitor/` and run `git checkout main`
        ```
        error: pathspec 'main' did not match any file(s) known to git.
        make: *** [checkout] Error 1
        ```

   3. Build cortx-monitor RPMs
        ```
        docker run --rm -v /var/artifacts:/var/artifacts -v ~/cortx:/cortx-workspace ghcr.io/seagate/cortx-build:centos-7.8.2003 make clean cortx-prvsnr cortx-monitor cortx-prereq release_build
        ```
        
        If you check the location `/var/artifacts/0/`, you will see that Cortx RPMs and 3rd party packages are generated.

        ```shell
        $ ll /var/artifacts/0/
        total 1608308
        drwxr-xr-x  13 root root       4096 Aug 19 05:16 3rd_party
        drwxr-xr-x   3 root root       4096 Aug 19 05:16 cortx_iso
        -rw-r--r--   1 root root      19416 Aug 19 05:16 install-2.0.0-0.sh
        drwxr-xr-x 198 root root       4096 Aug 19 05:16 python_deps
        -rw-r--r--   1 root root  241635505 Jun 15 08:45 python-deps-1.0.0-0.tar.gz
        -rw-r--r--   1 root root 1405229297 Jul  1 22:45 third-party-1.0.0-0.tar.gz
        ```
    
3. Install CORTX-Monitor RPMs

   SSPL has a `sspl_dev_deploy` script. We need to download and use it to deploy SSPL. Go to the home directory and run following commands.

    ```shell
    $ curl https://raw.githubusercontent.com/Seagate/cortx-monitor/main/low-level/files/opt/seagate/sspl/setup/sspl_dev_deploy -o sspl_dev_deploy
    $ chmod a+x sspl_dev_deploy
    ```
    **sspl_dev_deploy is only meant for dev purpose and to install SSPL independently along with its dependencies.**

4. Deploy SSPL RPMs.
    ```
    $ ./sspl_dev_deploy --cleanup
    $ ./sspl_dev_deploy --prereq -T file:///var/artifacts/0
    ```
    :page_with_curl: **Note:** 
    --cleanup includes removing cortx-py-utils RPM. Any other component RPMS installed on the setup will also get removed while removing cortx-py-utils.
   
   Create a template file with the name `~/sspl_deploy.conf`
    ```
    # 1-node config variable
    TMPL_CLUSTER_ID=CC01
    TMPL_NODE_ID=SN01
    TMPL_RACK_ID=RC01
    TMPL_SITE_ID=DC01
    TMPL_MACHINE_ID=0449364d92b2ba3915fcd8416014cff7
    TMPL_HOSTNAME=<your vm hostname>
    TMPL_NODE_NAME=srvnode-1
    TMPL_SERVER_NODE_TYPE=VM
    TMPL_MGMT_INTERFACE=eth0
    TMPL_MGMT_PUBLIC_FQDN=localhost
    TMPL_DATA_PRIVATE_FQDN=localhost
    TMPL_DATA_PRIVATE_INTERFACE=
    TMPL_DATA_PUBLIC_FQDN=localhost
    TMPL_DATA_PUBLIC_INTERFACE=
    TMPL_BMC_IP=
    TMPL_BMC_USER=
    TMPL_BMC_SECRET=""

    TMPL_ENCLOSURE_ID=enc_0449364d92b2ba3915fcd8416014cff7
    TMPL_ENCLOSURE_NAME=enclosure-1
    TMPL_ENCLOSURE_TYPE=VM
    TMPL_PRIMARY_CONTROLLER_IP=127.0.0.1
    TMPL_PRIMARY_CONTROLLER_PORT=28200
    TMPL_SECONDARY_CONTROLLER_IP=127.0.0.1
    TMPL_SECONDARY_CONTROLLER_PORT=28200
    TMPL_CONTROLLER_USER=manage
    TMPL_CONTROLLER_SECRET=""
    TMPL_CONTROLLER_TYPE=Gallium
    ```
    Make sure to update TMPL_MACHINE_ID, TMPL_HOSTNAME, TMPL_ENCLOSURE_ID, TMPL_BMC_SECRET, TMPL_CONTROLLER_SECRET with actual values.
    
    To generate passwords you can use below steps. The encryption keys are generated based on machine id and enclosure id. Feel free to use any sample machine id
    and enclosure id if actual IDs are not available.
  
    ```
    machine_id="xyz"
    enclosure_id="enc_xyz"
    bmc_pass='samplexxxx'
    encl_pass='samplexxxx'

    bmc_key=$(python3 -c 'from cortx.utils.security.cipher import Cipher; print(Cipher.generate_key('"'$machine_id'"', "server_node"))')
    encl_key=$(python3 -c 'from cortx.utils.security.cipher import Cipher; print(Cipher.generate_key('"'$enclosure_id'"', "storage_enclosure"))')

    #Encryption
    encl_encrypt_pass=$(python3 -c 'from cortx.utils.security.cipher import Cipher; print(Cipher.encrypt('$encl_key', '"'$encl_pass'"'.encode()).decode("utf-8"))')
    bmc_encrypt_pass=$(python3 -c 'from cortx.utils.security.cipher import Cipher; print(Cipher.encrypt('$bmc_key', '"'$bmc_pass'"'.encode()).decode("utf-8"))')

    echo "BMC_SECRET: "$bmc_encrypt_pass
    echo "ENCL_SECRET: "$encl_encrypt_pass
    ```
    Finally run the deployment script
    ```
    $ ./sspl_dev_deploy --deploy -T file:///var/artifacts/0 --variable_file ~/sspl_deploy.conf --storage_type RBOD --server_type HW
    ```

4. To start the CORTX-Monitor service, run the commands:

    ```shell
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

      `$ /opt/seagate/cortx/sspl/bin/sspl_setup test --config yaml:///etc/sspl_global_config_copy.yaml --plan dev_sanity`

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

## 1.5 Development Cycle
There are two options to build again after editing the code.

1. You can go the checkout location `~/cortx/cortx-monitor`, checkout any branch, edit the code, and follow below steps.
    ```
    $ ./sspl_dev_deploy --cleanup
    $ ./sspl_dev_deploy --prereq -T file:///var/artifacts/0
    $ ./sspl_dev_deploy --deploy -T file:///var/artifacts/0 --variable_file ~/sspl_deploy.conf --storage_type RBOD --server_type HW
    ```

2. To build only SSPL, you can follow below steps.
    1. Go to sspl repo root directory.
    2. Edit the code.
    3. Build SSPL using `./jenkins/build.sh`
    4. Copy RPMs from `~/rpmbuild/RPMS/` to `~/MYRPMS`
    5. Build deploy RPMs from local using belew steps.
    ```
    $ ./sspl_dev_deploy --cleanup
    $ ./sspl_dev_deploy --prereq -L ~/MYRPMS
    $ ./sspl_dev_deploy --deploy -L ~/MYRPMS --variable_file ~/sspl_deploy.conf --storage_type RBOD --server_type HW
    ```
    6. Repeat the same cycle.

## You're All Set & You're Awesome!

We thank you for stopping by to check out the CORTX Community. We are fully dedicated to our mission to build open source technologies that help the world save unlimited data and solve challenging data problems. Join our mission to help reinvent a data-driven world.

### Contribute to CORTX-Monitor

Please refer to the [CORTX Contribution Guide](https://github.com/Seagate/cortx/blob/main/CONTRIBUTING.md) to contribute to the CORTX Project and join our movement to make data storage better, efficient, and more accessible.

### Reach Out to Us

Please refer to the [Support](SUPPORT.md) section to reach out to us with your questions, feedback, and issues.
