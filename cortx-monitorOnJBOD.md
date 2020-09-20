# CORTX-Monitor Setup on JBOD

CORTX-Monitor monitors just physical disks and virtual disks if the JBOD is connected and the PSU,Fans,Disks and RAID-1 + integrity check for the node server is disabled by default in the JBOD environment.

This guide provides a step-by-step walkthrough for getting you CORTX-Monitor Server-ready for JBOD environment.

- [1.0 Prerequisites](#10-Prerequisites)
- [1.1 Clone the cortx-monitor repository](#11-Clone-the-cortx-monitor-repository)
- [1.2 Build the cortx-monitor source code](#12-Build-the-cortx-monitor-source-code)
- [1.3 Install CORTX-Monitor RPMs](#13-Install-CORTX-Monitor-RPMs)
- [1.4 Start CORTX-Monitor service](#14-Start-CORTX-Monitor-service)


## 1.0 Prerequisites

Please refer **Prerequisites** section from [CORTX-Monitor Quickstart Guide](https://github.com/Seagate/cortx-monitor/blob/dev/cortx-monitorQuickstartGuide.md#10-prerequisites)


## 1.1 Clone the cortx-monitor repository

Please refer **Clone the cortx-monitor repository** section from [CORTX-Monitor Quickstart Guide](https://github.com/Seagate/cortx-monitor/blob/dev/cortx-monitorQuickstartGuide.md#12-clone-the-cortx-monitor-repository)


## 1.2 Build the cortx-monitor source code

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

    Switch to the directory where you've cloned cortx-monitor and run the command:

    ```shell
    $ jenkins/build.sh
    ```

## 1.3 Install CORTX-Monitor RPMs

- You'll need to create a repository and copy all the required RPMs to it. Run the commands:

    ```shell
    $ mkdir MYRPMS
    $ cp -R /root/rpmbuild/RPMS/x86_64/cortx-libsspl_sec-* /root/rpmbuild/RPMS/noarch/cortx-sspl-* MYRPMS
    $ find MYRPMS -name \*.rpm -print0 | sudo xargs -0 yum install -y
    ```

## 1.4 Start CORTX-Monitor service

1. Before starting CORTX-Monitor service, ensure rabbitmq-server, provisioner and CORTX-Monitor rpms are installed on system and salt API is available on setup.

    ```shell

    $ rpm -qa | grep -Ei "rabbitmq|sspl|prvsnr"

    cortx-libsspl_sec-1.0.0xxxxxxxxxxxxxxxxxxxxx
    cortx-libsspl_sec-method_none-1.0.0xxxxxxxxxxxxxxx
    cortx-prvsnr-cli-1.0.0xxxxxxxxxxxxxxxxxxx
    cortx-prvsnr-1.0.0xxxxxxxxxxxxxxxxx
    cortx-sspl-1.0.0xxxxxxxxxxxxxxxx
    cortx-sspl-test-1.0.0xxxxxxxxxxxxxxxxxxxxxxxx
    rabbitmq-server-xxxxxxxxxxxxxxxxxx
    ```

    If provisioner is not installed on setup please follow below steps:

    <details>
    <summary>Click to expand!</summary>
    <p>

    #### Install Provisioner

    ```shell

    $ pkg_name="cortx-prvsnr-cli-1.0.0"
    $ build_url="http://cortx-storage.colo.seagate.com/releases/cortx/github/release/rhel-7.7.1908/last_successful"
    $ yum install -y $build_url/$(curl -s $build_url/|grep $pkg_name|sed 's/<\/*[^"]*"//g'|cut -d"\"" -f1)
    $ sudo /opt/seagate/cortx/provisioner/cli/src/setup-provisioner -S $build_url
    $ salt-call state.apply components.system
    $ python3 /opt/seagate/cortx/provisioner/cli/pillar_encrypt
    ```
    </p>
    </details>


    Check consul agent(process) is running

    ```shell
    $ ps aux | grep "consul"
    ```
    If consul is not running then execute below command to start consul.

    ```shell
    $ /opt/seagate/cortx/sspl/bin/sspl_setup_consul -e DEV
    ```

2. Configure CORTX-Monitor service

- To configure CORTX-Monitor service in DEV env:    
    `$ /opt/seagate/cortx/sspl/bin/sspl_setup post_install -p LDR_R1 -e DEV`

- To configure CORTX-Monitor service in PROD env:
    `$ /opt/seagate/cortx/sspl/bin/sspl_setup post_install -p LDR_R1`

- `$ /opt/seagate/cortx/sspl/bin/sspl_setup init -r cortx`
- `$ /opt/seagate/cortx/sspl/bin/sspl_setup config -f`

3. Configure Rabbitmq-server

- Check erlang.cookie file exists

    ```shell
    $ cat /var/lib/rabbitmq/.erlang.cookie
    ```

- For setting current node as cluster

    ```shell
    $ /opt/seagate/cortx/sspl/bin/setup_rabbitmq_cluster
    ```

- For setting 2 nodes in cluster

    ```shell
    $ /opt/seagate/cortx/sspl/bin/setup_rabbitmq_cluster -n NODES
    ```

:page_with_curl:**Note:** -n NODES where NODES must be hostname of those nodes and separated by comma. I.e. -n node-1,node-2

- Rabbitmq cluster status

    ```shell
    $ rabbitmqctl cluster_status
    ```

- Start rabbitmq-server

    ```shell

    $ systemctl start rabbitmq-server
    $ systemctl status rabbitmq-server -l
    ```

4. Start CORTX-Monitor service

    ```shell

    $ systemctl start sspl-ll
    $ systemctl status sspl-ll -l
    $ echo "state=active" > /var/$PRODUCT_FAMILY/sspl/data/state.txt
    $ PID=`/sbin/pidof -s /usr/bin/sspl_ll_d`
    $ kill -s SIGHUP $PID
    ```

5. Run sanity test and verify all tests are passed

    Check CORTX-Monitor configuration is successful

    ```shell
    $ /opt/seagate/cortx/sspl/bin/sspl_setup check 
    ```

    Run Sanity test

    ```shell
    $ /opt/seagate/cortx/sspl/bin/sspl_test sanity
    ```

