#!/bin/bash

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

MOCK_SERVER_IP=127.0.0.1
MOCK_SERVER_PORT=28200
RMQ_SELF_STARTED=0
RMQ_SELF_STOPPED=0
IS_VIRTUAL=$(facter is_virtual)

[[ $EUID -ne 0 ]] && sudo=sudo
script_dir=$(dirname $0)
source $script_dir/constants.sh
SSPL_STORE_TYPE=confstor

plan=${1:-}
avoid_rmq=${2:-}

common_config=yaml:///etc/cortx/sample_global_cortx_config.yaml
test_config=yaml:///opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.conf.yaml
sspl_config=yaml:///etc/cortx/sspl.conf

flask_help()
{
 echo "Check if prior Flask version was installed using yum
       rpm -qa | grep python-flask"
 echo "If packge detail appears, uninstall Flask using command
       yum remove python-flask"
 echo "If package details doesn't appear, then it was installed using pip3.6"
 echo "You can check Flask version using pip3.6 with following command
       pip3.6 freeze | grep flask"
 echo "Uninstall previously installed Flask version using
       pip3.6 uninstall flask"
 echo -e "In a similar way, uninstall all its dependencies using pip3.6:
          pip3.6 uninstall Werkzeug
          pip3.6 uninstall Jinja2
          pip3.6 uninstall itsdangerous"
}

pre_requisites()
{
    # copy RMQ password to sspl_test/config
    if [ "$SSPL_STORE_TYPE" == "consul" ]; then
        pw=$($CONSUL_PATH/consul kv get sspl/config/RABBITMQINGRESSPROCESSOR/password)
        $CONSUL_PATH/consul kv put sspl_test/config/RABBITMQINGRESSPROCESSORTESTS/password $pw
        pw=$($CONSUL_PATH/consul kv get sspl/config/RABBITMQEGRESSPROCESSOR/password)
        $CONSUL_PATH/consul kv put sspl_test/config/RABBITMQEGRESSPROCESSOR/password $pw
    fi
    if [ "$IS_VIRTUAL" == "true" ]
    then
        # Backing up original persistence data
        $sudo rm -rf /var/$PRODUCT_FAMILY/sspl/orig-data
        $sudo mkdir -p /var/$PRODUCT_FAMILY/sspl/orig-data
        $sudo find /var/$PRODUCT_FAMILY/sspl -maxdepth 2 -type d -path "/var/$PRODUCT_FAMILY/sspl/data/*" -not -name 'iem'  -exec bash -c 'mv -f ${0} ${0/data/orig-data}/' {} \;
        $sudo mkdir -p /var/$PRODUCT_FAMILY/sspl/orig-data/iem
        if [ -f /var/$PRODUCT_FAMILY/sspl/data/iem/last_processed_msg_time ]; then
            $sudo mv /var/$PRODUCT_FAMILY/sspl/data/iem/last_processed_msg_time /var/$PRODUCT_FAMILY/sspl/orig-data/iem/last_processed_msg_time
        fi
    fi

    systemctl status rabbitmq-server 1>/dev/null && export status=true || export status=false

    if [ -z "$avoid_rmq" ]; then
        # Start rabbitmq if not already running
        if [ "$status" = "false" ]; then
            echo "Starting rabbitmq server as needed for tests"
            systemctl start rabbitmq-server
            RMQ_SELF_STARTED=1
        fi
    else
        # Stop rabbitmq if running already
        if [ "$status" = "true" ]; then
            echo "Stopping rabbitmq server as needed for tests"
            systemctl stop rabbitmq-server
            RMQ_SELF_STOPPED=1
        fi
    fi

    # Enable ipmi simulator
    if [ "$IS_VIRTUAL" == "true" ]
    then
        cp -Rp $script_dir/ipmi_simulator/ipmisimtool /usr/bin
        touch /tmp/activate_ipmisimtool
    fi

    if [ "$IS_VIRTUAL" == "true" -a "$SSPL_STORE_TYPE" == "consul" ]
    then
        # clearing $CONSUL_PATH/consul keys.
        $CONSUL_PATH/consul kv delete -recurse var/$PRODUCT_FAMILY/sspl/data
        # clearing consul keys.
        $CONSUL_PATH/consul kv delete -recurse var/$PRODUCT_FAMILY/sspl/data
    fi
}

deleteMockedInterface()
{
    ip link show eth-mocked
    if [ $? == 0 ]
    then
        ip link delete eth-mocked 2>/dev/null
    fi
}

kill_mock_server()
{
    # Kill mock API server
    pkill -f \./mock_server
}

restore_cfg_services()
{
    # Restoring MC port to value stored before tests
    if [ "$SSPL_STORE_TYPE" == "file" ]
    then
        port=$(sed -n -e '/primary_controller_port/ s/.*\: *//p' /etc/cortx/sspl.conf)
        if [ "$port" == "$MOCK_SERVER_PORT" ]
        then
            sed -i 's/primary_controller_ip: '"$MOCK_SERVER_IP"'/primary_controller_ip: '"$primary_ip"'/g' /etc/cortx/sspl.conf
            sed -i 's/primary_controller_port: '"$MOCK_SERVER_PORT"'/primary_controller_port: '"$primary_port"'/g' /etc/cortx/sspl.conf
        fi
        # Removing updated system information from sspl_tests.yaml
        # This is required otherwise, everytime if we run sanity, key-value
        # pairs will be appended which will break the sanity.
        # Also, everytime, updated values from /etc/cortx/sspl.conf should be updated.
        sed -i 's/node_id: '"$node_id"'/node_id: 001/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.yaml
        sed -i 's/rack_id: '"$rack_id"'/rack_id: 001/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.yaml
        sed -i 's/site_id: '"$site_id"'/site_id: 001/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.yaml
        sed -i 's/cluster_id: '"$cluster_id"'/cluster_id: 001/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.yaml
    elif [ "$SSPL_STORE_TYPE" == "confstor" ]
    then
        port=`conf $common_config get "storage>$encl_id>controller>primary>port"`
        port=$(echo $port | tr -d "["\" | tr -d "\"]")
        if [ "$port" == "$MOCK_SERVER_PORT" ]
        then
            conf $common_config set "storage>$encl_id>controller>primary>port=$primary_port"
            conf $common_config set "storage>$encl_id>controller>primary>ip=$primary_ip"
        fi
        conf $test_config set "SYSTEM_INFORMATION>node_id=001"
        conf $test_config set "SYSTEM_INFORMATION>site_id=001"
        conf $test_config set "SYSTEM_INFORMATION>rack_id=001"
        conf $test_config set "SYSTEM_INFORMATION>cluster_id=001"
    else
        $CONSUL_PATH/consul kv put sspl/config/STORAGE_ENCLOSURE/controller/primary_mc/ip $primary_ip
        port=$($CONSUL_PATH/consul kv get sspl/config/STORAGE_ENCLOSURE/controller/primary_mc/port)
        if [ "$port" == "$MOCK_SERVER_PORT" ]
        then
            $CONSUL_PATH/consul kv put sspl/config/STORAGE_ENCLOSURE/controller/primary_mc/port $primary_port
        fi
        $CONSUL_PATH/consul kv put sspl_test/config/SYSTEM_INFORMATION/node_id '001'
        $CONSUL_PATH/consul kv put sspl_test/config/SYSTEM_INFORMATION/site_id '001'
        $CONSUL_PATH/consul kv put sspl_test/config/SYSTEM_INFORMATION/rack_id '001'
        $CONSUL_PATH/consul kv put sspl_test/config/SYSTEM_INFORMATION/cluster_id '001'
    fi

    if [ "$IS_VIRTUAL" == "true" ]
    then
        echo "Stopping mock server"
        kill_mock_server
        deleteMockedInterface
    fi

    if [ "$RMQ_SELF_STARTED" -eq 1 ]
    then
        echo "Stopping rabbitmq server as was started for tests"
        systemctl stop rabbitmq-server
        RMQ_SELF_STARTED=0
    fi

    if [ "$RMQ_SELF_STOPPED" -eq 1 ]
    then
        echo "Starting rabbitmq server as was stopped for tests"
        systemctl start rabbitmq-server
        RMQ_SELF_STOPPED=0
    fi

    # Remove ipmisimtool
    rm -f /usr/bin/ipmisimtool
    rm -f /tmp/activate_ipmisimtool

    # Restore $CONSUL_PATH/consul data
    if [ "$IS_VIRTUAL" == "true" -a "$SSPL_STORE_TYPE" == "consul" ]
    then
        $CONSUL_PATH/consul kv delete -recurse var/$PRODUCT_FAMILY/sspl/data
        $CONSUL_PATH/consul kv import @/tmp/consul_backup.json
        $sudo rm -f /tmp/consul_backup.json
    fi
}

cleanup()
{
    restore_cfg_services
}

trap cleanup 1 2 3 6 9 15

execute_test()
{
    $sudo $script_dir/run_sspl-ll_tests.sh $plan
}

if [ "$SSPL_STORE_TYPE" == "confstor" ]
then
    # Read common key which are needed to fetch confstor config.
    machine_id=`cat /etc/machine-id`
    minion_id=`conf $common_config get "cluster>server_nodes>$machine_id"`
    minion_id=$(echo $minion_id | tr -d "["\" | tr -d "\"]")
    encl_id=`conf $common_config get "cluster>$minion_id>storage>enclosure_id"`
    encl_id=$(echo $encl_id | tr -d "["\" | tr -d "\"]")
fi

flask_installed=$(python3.6 -c 'import pkgutil; print(1 if pkgutil.find_loader("flask") else 0)')
[ $flask_installed = "1" ] && [ $(python3.6 -c 'import flask; print(flask.__version__)') = "1.1.1" ] || {
    flask_help
    echo "Please install Flask 1.1.1 using
          pip3.6 install flask==1.1.1"
    echo -e "\n"
    exit 1
}

# Onward LDR_R2, consul will be abstracted out and won't exist as hard dependency of SSPL
[ "$PRODUCT_NAME" == "LDR_R1" ] && python3 $script_dir/put_config_to_consul.py

# Take backup of original sspl.conf
[[ -f /etc/cortx/sspl.conf ]] && $sudo cp /etc/cortx/sspl.conf /etc/cortx/sspl.conf.back
[[ -f /etc/cortx/sample_global_cortx_config.yaml ]] && $sudo cp /etc/cortx/sample_global_cortx_config.yaml /etc/cortx/sample_global_cortx_config.yaml.back

# check the port configured in consul
# if virtual machine, change the port to $MOCK_SERVER_PORT as mock_server runs on $MOCK_SERVER_PORT
if [ "$SSPL_STORE_TYPE" == "consul" ]
then
    primary_ip=$($CONSUL_PATH/consul kv get sspl/config/STORAGE_ENCLOSURE/controller/primary_mc/ip)
    primary_port=$($CONSUL_PATH/consul kv get sspl/config/STORAGE_ENCLOSURE/controller/primary_mc/port)
    if [ "$IS_VIRTUAL" == "true" ]
    then
        $CONSUL_PATH/consul kv put sspl/config/STORAGE_ENCLOSURE/controller/primary_mc/ip $MOCK_SERVER_IP
        if [ "$primary_port" != "$MOCK_SERVER_PORT" ]
        then
            $CONSUL_PATH/consul kv put sspl/config/STORAGE_ENCLOSURE/controller/primary_mc/port $MOCK_SERVER_PORT
        fi
    fi
elif [ "$SSPL_STORE_TYPE" == "confstor" ]
then
    primary_ip=`conf $common_config get "storage>$encl_id>controller>primary>ip"`
    primary_ip=$(echo $primary_ip | tr -d "["\" | tr -d "\"]")
    primary_port=`conf $common_config get "storage>$encl_id>controller>primary>port"`
    primary_port=$(echo $primary_port | tr -d "["\" | tr -d "\"]")
    if [ "$IS_VIRTUAL" == "true" ]
    then
        if [ "$primary_port" != "$MOCK_SERVER_PORT" ]
        then
            conf $common_config set "storage>$encl_id>controller>primary>port=$MOCK_SERVER_PORT"
            conf $common_config set "storage>$encl_id>controller>primary>ip=$MOCK_SERVER_IP"
        fi
    fi
else
    primary_ip=$(sed -n -e '/primary_controller_ip/ s/.*\: *//p' /etc/cortx/sspl.conf)
    primary_port=$(sed -n -e '/primary_controller_port/ s/.*\: *//p' /etc/cortx/sspl.conf)
    if [ "$IS_VIRTUAL" == "true" ]
    then
        if [ "$primary_port" != "$MOCK_SERVER_PORT" ]
        then
            sed -i 's/primary_controller_ip: '"$primary_ip"'/primary_controller_ip: '"$MOCK_SERVER_IP"'/g' /etc/cortx/sspl.conf
            sed -i 's/primary_controller_port: '"$primary_port"'/primary_controller_port: '"$MOCK_SERVER_PORT"'/g' /etc/cortx/sspl.conf
        fi
    fi
fi

# Setting pre-requisites first
pre_requisites

# Start mock API server if virtual machine
if [ "$IS_VIRTUAL" == "true" ]
then
    echo "Starting mock server on 127.0.0.1:$MOCK_SERVER_PORT"
    $script_dir/mock_server &
fi

# IMP NOTE: Please make sure that SSPL conf file has
# primary_controller_ip=127.0.0.1 and primary_controller_port=$MOCK_SERVER_PORT (for vm)
# For sanity test SSPL should connect to mock server instead of real server (for vm)
# Restart SSPL to re-read configuration
if [ "$SSPL_STORE_TYPE" == "consul" ]
then
    # Find the nodename
    if [ "$PRODUCT_NAME" == "LDR_R1" ]; then
        SRVNODE="$(sudo salt-call grains.get id --output=newline_values_only)"
    else
        SRVNODE="$(consul kv get system_information/salt_minion_id)"
    fi
    if [ -z "$SRVNODE" ];then
        SRVNODE="$(cat /etc/salt/minion_id)"
        if [ -z "$SRVNODE" ];then
            SRVNODE="srvnode-1"
        fi
    fi
    transmit_interval=$($CONSUL_PATH/consul kv get sspl/config/NODEDATAMSGHANDLER/transmit_interval)
    disk_usage_threshold=$($CONSUL_PATH/consul kv get sspl/config/NODEDATAMSGHANDLER/disk_usage_threshold)
    host_memory_usage_threshold=$($CONSUL_PATH/consul kv get sspl/config/NODEDATAMSGHANDLER/host_memory_usage_threshold)
    cpu_usage_threshold=$($CONSUL_PATH/consul kv get sspl/config/NODEDATAMSGHANDLER/cpu_usage_threshold)
    rack_id=$($CONSUL_PATH/consul kv get system_information/rack_id)
    site_id=$($CONSUL_PATH/consul kv get system_information/site_id)
    node_id=$($CONSUL_PATH/consul kv get system_information/$SRVNODE/node_id)
    cluster_id=$($CONSUL_PATH/consul kv get system_information/cluster_id)
elif [ "$SSPL_STORE_TYPE" == "confstor" ]
then
    transmit_interval=`conf $sspl_config get "NODEDATAMSGHANDLER>transmit_interval"`
    transmit_interval=$(echo $transmit_interval | tr -d "["\" | tr -d "\"]")
    disk_usage_threshold=`conf $sspl_config get "NODEDATAMSGHANDLER>disk_usage_threshold"`
    disk_usage_threshold=$(echo $disk_usage_threshold | tr -d "["\" | tr -d "\"]")
    host_memory_usage_threshold=`conf $sspl_config get "NODEDATAMSGHANDLER>host_memory_usage_threshold"`
    host_memory_usage_threshold=$(echo $host_memory_usage_threshold| tr -d "["\" | tr -d "\"]")
    cpu_usage_threshold=`conf $sspl_config get "NODEDATAMSGHANDLER>cpu_usage_threshold"`
    cpu_usage_threshold=$(echo $cpu_usage_threshold | tr -d "["\" | tr -d "\"]")
    node_id=`conf $common_config get "cluster>$minion_id>node_id"`
    node_id=$(echo $node_id | tr -d "["\" | tr -d "\"]")
    site_id=`conf $common_config get "cluster>$minion_id>site_id"`
    site_id=$(echo $site_id | tr -d "["\" | tr -d "\"]")
    rack_id=`conf $common_config get "cluster>$minion_id>rack_id"`
    rack_id=$(echo $rack_id | tr -d "["\" | tr -d "\"]")
    cluster_id=`conf $common_config get "cluster>cluster_id"`
    cluster_id=$(echo $cluster_id | tr -d "["\" | tr -d "\"]")
    primary_controller_ip=`conf $common_config get "storage>$encl_id>controller>primary>ip"`
    primary_controller_ip=$(echo $primary_controller_ip | tr -d "["\" | tr -d "\"]")
else
    transmit_interval=$(sed -n -e '/transmit_interval/ s/.*\: *//p' /etc/cortx/sspl.conf)
    disk_usage_threshold=$(sed -n -e '/disk_usage_threshold/ s/.*\: *//p' /etc/cortx/sspl.conf)
    host_memory_usage_threshold=$(sed -n -e '/host_memory_usage_threshold/ s/.*\: *//p' /etc/cortx/sspl.conf)
    cpu_usage_threshold=$(sed -n -e '/cpu_usage_threshold/ s/.*\: *//p' /etc/cortx/sspl.conf)
    rack_id=$(sed -n -e '/rack_id/ s/.*\: *//p' /etc/cortx/sspl.conf)
    site_id=$(sed -n -e '/site_id/ s/.*\: *//p' /etc/cortx/sspl.conf)
    node_id=$(sed -n -e '/node_id/ s/.*\: *//p' /etc/cortx/sspl.conf)
    cluster_id=$(sed -n -e '/cluster_id/ s/.*\: *//p' /etc/cortx/sspl.conf)
    cluster_nodes=$(sed -n -e '/cluster_nodes/ s/.*\: *//p' /etc/cortx/sspl.conf)
    primary_controller_ip=$(sed -n -e '/primary_controller_ip/ s/.*\: *//p' /etc/cortx/sspl.conf)
fi

# setting values for testing
if [ "$IS_VIRTUAL" == "true" ]
then
    disk_out=`python3.6 -c "import psutil; print(int(psutil.disk_usage('/')[3]-2))"`
    $sudo $script_dir/set_threshold.sh "10" $disk_out "0" "0" $sspl_config
fi

if [ "$SSPL_STORE_TYPE" == "consul" ]
then
    # Update consul with updated System Information
    # append above parsed key-value pairs in consul under [SYSTEM_INFORMATION] section
    $CONSUL_PATH/consul kv put sspl_test/config/SYSTEM_INFORMATION/node_id $node_id
    $CONSUL_PATH/consul kv put sspl_test/config/SYSTEM_INFORMATION/site_id $site_id
    $CONSUL_PATH/consul kv put sspl_test/config/SYSTEM_INFORMATION/rack_id $rack_id
    $CONSUL_PATH/consul kv put sspl_test/config/SYSTEM_INFORMATION/cluster_id $cluster_id
    # updateing rabbitmq cluster
    CLUSTER_NODES=$($CONSUL_PATH/consul kv get sspl/config/RABBITMQCLUSTER/cluster_nodes)
    $CONSUL_PATH/consul kv put sspl_test/config/RABBITMQCLUSTER/cluster_nodes $CLUSTER_NODES
elif [ "$SSPL_STORE_TYPE" == "confstor" ]
then
    conf $test_config set "SYSTEM_INFORMATION>node_id=$node_id"
    conf $test_config set "SYSTEM_INFORMATION>site_id=$site_id"
    conf $test_config set "SYSTEM_INFORMATION>rack_id=$rack_id"
    conf $test_config set "SYSTEM_INFORMATION>cluster_id=$cluster_id"
    CLUSTER_NODES=`conf $sspl_config get "RABBITMQCLUSTER>cluster_nodes"`
    CLUSTER_NODES=$(echo $CLUSTER_NODES | tr -d "["\" | tr -d "\"]")
    conf $test_config set "RABBITMQCLUSTER>cluster_nodes=$CLUSTER_NODES"
else
    # Update sspl_tests.yaml with updated System Information
    # append above parsed key-value pairs in sspl_tests.yaml under [SYSTEM_INFORMATION] section
    sed -i 's/node_id: .*/node_id: '"$node_id"'/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.yaml
    sed -i 's/site_id: 001/site_id: '"$site_id"'/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.yaml
    sed -i 's/rack_id: 001/rack_id: '"$rack_id"'/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.yaml
    sed -i 's/cluster_id: .*/cluster_id: '"$cluster_id"'/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.yaml
    sed -i 's/cluster_nodes: localhost/cluster_nodes: '"$cluster_nodes"'/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.yaml
fi

if [ "$IS_VIRTUAL" == "true" ]
then
    echo "Restarting SSPL"
    $sudo systemctl restart sspl-ll
    echo "Waiting for SSPL to complete initialization of all the plugins.."
    $script_dir/rabbitmq_start_checker sspl-out sensor-key
fi

echo "Initialization completed. Starting tests"

# Switch SSPL to active state to resume all the suspended plugins. If SSPL is
# not switched to active state then plugins will not respond and tests will
# fail. Sending SIGUP to SSPL makes SSPL to read state file and switch state.
if [ "$IS_VIRTUAL" == "true" ]
then
    echo "state=active" > /var/$PRODUCT_FAMILY/sspl/data/state.txt
    PID=`/usr/bin/pgrep -d " " -f /usr/bin/sspl_ll_d`
    kill -s SIGHUP $PID
fi

# Start tests
execute_test $plan
retcode=$?

if [ "$IS_VIRTUAL" == "true" ]
then
    # Restoring original cache data
    $sudo find /var/$PRODUCT_FAMILY/sspl -maxdepth 2 -type d -path "/var/$PRODUCT_FAMILY/sspl/data/*" -not -name 'iem'  -exec bash -c 'rm -rf ${0}' {} \;
    $sudo find /var/$PRODUCT_FAMILY/sspl -maxdepth 2 -type d -path "/var/$PRODUCT_FAMILY/sspl/orig-data/*" -not -name 'iem'  -exec bash -c 'mv -f ${0} ${0/orig-data/data}/' {} \;
    if [ -f /var/$PRODUCT_FAMILY/sspl/orig-data/iem/last_processed_msg_time ]; then
        $sudo mv /var/$PRODUCT_FAMILY/sspl/orig-data/iem/last_processed_msg_time /var/$PRODUCT_FAMILY/sspl/data/iem/last_processed_msg_time
    fi
    $sudo rm -rf /var/$PRODUCT_FAMILY/sspl/orig-data
fi

if [ "$IS_VIRTUAL" == "true" ]
then
    # setting back the actual values
    $sudo $script_dir/set_threshold.sh $transmit_interval $disk_usage_threshold $host_memory_usage_threshold $cpu_usage_threshold $sspl_config
    [[ -f /etc/cortx/sspl.conf.back ]] && $sudo mv /etc/cortx/sspl.conf.back /etc/cortx/sspl.conf
    [[ -f /etc/cortx/sample_global_cortx_config.yaml.back ]] && $sudo mv /etc/cortx/sample_global_cortx_config.yaml.back /etc/cortx/sample_global_cortx_config.yaml
fi

echo "Tests completed, restored configs and services .."
restore_cfg_services

echo "Cleaned Up .."
exit $retcode