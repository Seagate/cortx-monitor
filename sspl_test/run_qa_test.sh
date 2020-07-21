#!/bin/bash

MOCK_SERVER_IP=127.0.0.1
MOCK_SERVER_PORT=28200
RMQ_SELF_STARTED=0
SSPL_STORE_TYPE=${SSPL_STORE_TYPE:-consul}

[[ $EUID -ne 0 ]] && sudo=sudo
script_dir=$(dirname $0)
. $script_dir/constants.sh

avoid_rmq=${1:-avoid_rmq}

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
    # Backing up original persistence data
    $sudo rm -rf /var/$PRODUCT_FAMILY/sspl/orig-data
    $sudo mkdir -p /var/$PRODUCT_FAMILY/sspl/orig-data
    $sudo find /var/$PRODUCT_FAMILY/sspl -maxdepth 2 -type d -path '/var/$PRODUCT_FAMILY/sspl/data/*' -not -name 'iem'  -exec bash -c 'mv -f ${0} ${0/data/orig-data}/' {} \;
    $sudo mkdir -p /var/$PRODUCT_FAMILY/sspl/orig-data/iem
    if [ -f /var/$PRODUCT_FAMILY/sspl/data/iem/last_processed_msg_time ]; then
        $sudo mv /var/$PRODUCT_FAMILY/sspl/data/iem/last_processed_msg_time /var/$PRODUCT_FAMILY/sspl/orig-data/iem/last_processed_msg_time
    fi

    if [ -z "$avoid_rmq" ]; then
        # Start rabbitmq if not already running
        systemctl status rabbitmq-server 1>/dev/null && export status=true || export status=false
        if [ "$status" = "false" ]; then
            echo "Starting rabbitmq server as needed for tests"
            systemctl start rabbitmq-server
            RMQ_SELF_STARTED=1
        fi
    fi

    # Enable ipmi simulator
    cp -Rp $script_dir/ipmi_simulator/ipmisimtool /usr/bin
    touch /tmp/activate_ipmisimtool
    # Backup /opt/seagate/<product>/sspl/bin/consul data before deleting
    $CONSUL_PATH/consul kv export var/$PRODUCT_FAMILY/sspl/data/ > /tmp/consul_backup.json

    # clearing /opt/seagate/<product>/sspl/bin/consul keys.
    $CONSUL_PATH/consul kv delete -recurse var/$PRODUCT_FAMILY/sspl/data
    # clearing consul keys.
    $CONSUL_PATH/consul kv delete -recurse var/$PRODUCT_FAMILY/sspl/data

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
        port=$(sed -n -e '/primary_controller_port/ s/.*\= *//p' /etc/sspl.conf)
        if [ "$port" == "$MOCK_SERVER_PORT" ]
        then
            sed -i 's/primary_controller_port='"$MOCK_SERVER_PORT"'/primary_controller_port='"$primary_port"'/g' /etc/sspl.conf
        fi
        # Removing updated system information from sspl_tests.conf
        # This is required otherwise, everytime if we run sanity, key-value
        # pairs will be appended which will break the sanity.
        # Also, everytime, updated values from /etc/sspl.conf should be updated.
        sed -i 's/node_id='"$node_id"'/node_id=001/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.conf
        sed -i 's/rack_id='"$rack_id"'/rack_id=001/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.conf
        sed -i 's/site_id='"$site_id"'/site_id=001/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.conf
        sed -i 's/cluster_id='"$cluster_id"'/cluster_id=001/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.conf
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

    echo "Stopping mock server"
    kill_mock_server
    deleteMockedInterface

    if [ "$RMQ_SELF_STARTED" -eq 1 ]
    then
        echo "Stopping rabbitmq server as was started for tests"
        systemctl stop rabbitmq-server
        RMQ_SELF_STARTED=0
    fi

    # Remove ipmisimtool
    rm -f /usr/bin/ipmisimtool
    rm -f /tmp/activate_ipmisimtool

    # Restore /opt/seagate/<product>/sspl/bin/consul data
    $CONSUL_PATH/consul kv delete -recurse var/$PRODUCT_FAMILY/sspl/data
    $CONSUL_PATH/consul kv import @/tmp/consul_backup.json
    $sudo rm -f /tmp/consul_backup.json
}

cleanup()
{
    restore_cfg_services
}

trap cleanup 1 2 3 6 9 15

execute_test()
{
    $sudo $script_dir/run_sspl-ll_tests.sh ${@:2}
}

flask_installed=$(python3.6 -c 'import pkgutil; print(1 if pkgutil.find_loader("flask") else 0)')
[ $flask_installed = "1" ] && [ $(python3.6 -c 'import flask; print(flask.__version__)') = "1.1.1" ] || {
    flask_help
    echo "Please install Flask 1.1.1 using
          pip3.6 install flask==1.1.1"
    echo -e "\n"
    exit 1
}

python3 $script_dir/put_config_to_consul.py

# Take backup of original sspl.conf
[[ -f /etc/sspl.conf ]] && $sudo cp /etc/sspl.conf /etc/sspl.conf.back

# check the port configured in consul
# change the port to $MOCK_SERVER_PORT as mock_server runs on $MOCK_SERVER_PORT
if [ "$SSPL_STORE_TYPE" == "consul" ]
then
    primary_ip=$($CONSUL_PATH/consul kv get sspl/config/STORAGE_ENCLOSURE/controller/primary_mc/ip)
    $CONSUL_PATH/consul kv put sspl/config/STORAGE_ENCLOSURE/controller/primary_mc/ip $MOCK_SERVER_IP
    primary_port=$($CONSUL_PATH/consul kv get sspl/config/STORAGE_ENCLOSURE/controller/primary_mc/port)
    if [ "$primary_port" != "$MOCK_SERVER_PORT" ]
    then
        $CONSUL_PATH/consul kv put sspl/config/STORAGE_ENCLOSURE/controller/primary_mc/port $MOCK_SERVER_PORT
    fi
else
    primary_port=$(sed -n -e '/primary_controller_port/ s/.*\= *//p' /etc/sspl.conf)
    if [ "$primary_port" != "$MOCK_SERVER_PORT" ]
    then
        sed -i 's/primary_controller_port='"$primary_port"'/primary_controller_port='"$MOCK_SERVER_PORT"'/g' /etc/sspl.conf
    fi
fi

# Setting pre-requisites first
pre_requisites

# Start mock API server
echo "Starting mock server on 127.0.0.1:$MOCK_SERVER_PORT"
$script_dir/mock_server &

# IMP NOTE: Please make sure that SSPL conf file has
# primary_controller_ip=127.0.0.1 and primary_controller_port=$MOCK_SERVER_PORT.
# For sanity test SSPL should connect to mock server instead of real server.
# Restart SSPL to re-read configuration
if [ "$SSPL_STORE_TYPE" == "consul" ]
then
    transmit_interval=$($CONSUL_PATH/consul kv get sspl/config/NODEDATAMSGHANDLER/transmit_interval)
    disk_usage_threshold=$($CONSUL_PATH/consul kv get sspl/config/NODEDATAMSGHANDLER/disk_usage_threshold)
    host_memory_usage_threshold=$($CONSUL_PATH/consul kv get sspl/config/NODEDATAMSGHANDLER/host_memory_usage_threshold)
    cpu_usage_threshold=$($CONSUL_PATH/consul kv get sspl/config/NODEDATAMSGHANDLER/cpu_usage_threshold)
    rack_id=$($CONSUL_PATH/consul kv get system_information/rack_id)
    site_id=$($CONSUL_PATH/consul kv get system_information/site_id)
    node_id=$($CONSUL_PATH/consul kv get system_information/srvnode-1/node_id)
    cluster_id=$($CONSUL_PATH/consul kv get system_information/cluster_id)
else
    transmit_interval=$(sed -n -e '/transmit_interval/ s/.*\= *//p' /etc/sspl.conf)
    disk_usage_threshold=$(sed -n -e '/disk_usage_threshold/ s/.*\= *//p' /etc/sspl.conf)
    host_memory_usage_threshold=$(sed -n -e '/host_memory_usage_threshold/ s/.*\= *//p' /etc/sspl.conf)
    cpu_usage_threshold=$(sed -n -e '/cpu_usage_threshold/ s/.*\= *//p' /etc/sspl.conf)
    rack_id=$(sed -n -e '/rack_id/ s/.*\= *//p' /etc/sspl.conf)
    site_id=$(sed -n -e '/site_id/ s/.*\= *//p' /etc/sspl.conf)
    node_id=$(sed -n -e '/node_id/ s/.*\= *//p' /etc/sspl.conf)
    cluster_id=$(sed -n -e '/cluster_id/ s/.*\= *//p' /etc/sspl.conf)
fi

# setting values for testing
disk_out=`python3.6 -c "import psutil; print(int(psutil.disk_usage('/')[3]-2))"`
$sudo $script_dir/set_threshold.sh "10" $disk_out "0" "0"

if [ "$SSPL_STORE_TYPE" == "consul" ]
then
    # Update consul with updated System Information
    # append above parsed key-value pairs in consul under [SYSTEM_INFORMATION] section
    $CONSUL_PATH/consul kv put sspl_test/config/SYSTEM_INFORMATION/node_id $node_id
    $CONSUL_PATH/consul kv put sspl_test/config/SYSTEM_INFORMATION/site_id $site_id
    $CONSUL_PATH/consul kv put sspl_test/config/SYSTEM_INFORMATION/rack_id $rack_id
    $CONSUL_PATH/consul kv put sspl_test/config/SYSTEM_INFORMATION/cluster_id $cluster_id
else
    # Update sspl_tests.conf with updated System Information
    # append above parsed key-value pairs in sspl_tests.conf under [SYSTEM_INFORMATION] section
    sed -i 's/node_id=001/node_id='"$node_id"'/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.conf
    sed -i 's/site_id=001/site_id='"$site_id"'/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.conf
    sed -i 's/rack_id=001/rack_id='"$rack_id"'/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.conf
    sed -i 's/cluster_id=001/cluster_id='"$cluster_id"'/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.conf
fi

# updateing rabbitmq cluster
CLUSTER_NODES=$($CONSUL_PATH/consul kv get sspl/config/RABBITMQCLUSTER/cluster_nodes)
$CONSUL_PATH/consul kv put sspl_test/config/RABBITMQCLUSTER/cluster_nodes $CLUSTER_NODES

echo "Restarting SSPL"
$sudo systemctl restart sspl-ll
echo "Waiting for SSPL to complete initialization of all the plugins"
$script_dir/rabbitmq_start_checker sspl-out sensor-key
echo "Initialization completed. Starting tests"

# Switch SSPL to active state to resume all the suspended plugins. If SSPL is
# not switched to active state then plugins will not respond and tests will
# fail. Sending SIGUP to SSPL makes SSPL to read state file and switch state.
echo "state=active" > /var/$PRODUCT_FAMILY/sspl/data/state.txt
PID=`/sbin/pidof -s /usr/bin/sspl_ll_d`
kill -s SIGHUP $PID

# Start tests
execute_test $*
retcode=$?

# Restoring original cache data
$sudo find /var/$PRODUCT_FAMILY/sspl -maxdepth 2 -type d -path '/var/$PRODUCT_FAMILY/sspl/data/*' -not -name 'iem'  -exec bash -c 'rm -rf ${0}' {} \;
$sudo find /var/$PRODUCT_FAMILY/sspl -maxdepth 2 -type d -path '/var/$PRODUCT_FAMILY/sspl/orig-data/*' -not -name 'iem'  -exec bash -c 'mv -f ${0} ${0/orig-data/data}/' {} \;
if [ -f /var/$PRODUCT_FAMILY/sspl/orig-data/iem/last_processed_msg_time ]; then
    $sudo mv /var/$PRODUCT_FAMILY/sspl/orig-data/iem/last_processed_msg_time /var/$PRODUCT_FAMILY/sspl/data/iem/last_processed_msg_time
fi
$sudo rm -rf /var/$PRODUCT_FAMILY/sspl/orig-data

# setting back the actual values
$sudo $script_dir/set_threshold.sh $transmit_interval $disk_usage_threshold $host_memory_usage_threshold $cpu_usage_threshold
[[ -f /etc/sspl.conf.back ]] && $sudo mv /etc/sspl.conf.back /etc/sspl.conf

echo "Tests completed, restored configs and services .."
restore_cfg_services

echo "Cleaned Up .."
exit $retcode
