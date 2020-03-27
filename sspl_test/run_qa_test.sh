#!/bin/bash

MOCK_SERVER_PORT=28200
RMQ_SELF_STARTED=0
SSPL_STORE_TYPE=${SSPL_STORE_TYPE:-consul}

rack_id=$(/opt/seagate/eos/hare/bin/consul kv get sspl.SYSTEM_INFORMATION.rack_id)
site_id=$(/opt/seagate/eos/hare/bin/consul kv get sspl.SYSTEM_INFORMATION.site_id)
node_id=$(/opt/seagate/eos/hare/bin/consul kv get sspl.SYSTEM_INFORMATION.node_id)
cluster_id=$(/opt/seagate/eos/hare/bin/consul kv get sspl.SYSTEM_INFORMATION.cluster_id)

[[ $EUID -ne 0 ]] && sudo=sudo
script_dir=$(dirname $0)

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
    $sudo rm -rf /var/eos/sspl/orig-data
    $sudo mkdir -p /var/eos/sspl/orig-data
    $sudo find /var/eos/sspl -maxdepth 2 -type d -path '/var/eos/sspl/data/*' -not -name 'iem'  -exec bash -c 'mv -f ${0} ${0/data/orig-data}/' {} \;
    $sudo mkdir -p /var/eos/sspl/orig-data/iem
    if [ -f /var/eos/sspl/data/iem/last_processed_msg_time ]; then
        $sudo mv /var/eos/sspl/data/iem/last_processed_msg_time /var/eos/sspl/orig-data/iem/last_processed_msg_time
    fi

    # Start rabbitmq if not already running
    systemctl status rabbitmq-server 1>/dev/null && export status=true || export status=false
    if [ "$status" = "false" ]; then
        echo "Starting rabbitmq server as needed for tests"
        systemctl start rabbitmq-server
        RMQ_SELF_STARTED=1
    fi

    # Enable ipmi simulator
    cp -Rp $script_dir/ipmi_simulator/ipmisimtool /usr/bin
    touch /tmp/activate_ipmisimtool
    # Backup /opt/seagate/eos/hare/bin/consul data before deleting
    /opt/seagate/eos/hare/bin/consul kv export var/eos/sspl/data/ > /tmp/consul_backup.json

    # clearing /opt/seagate/eos/hare/bin/consul keys.
    /opt/seagate/eos/hare/bin/consul kv delete -recurse var/eos/sspl/data
    # clearing consul keys.
    /opt/seagate/eos/hare/bin/consul kv delete -recurse var/eos/sspl/data

    # Update sspl_tests.conf with Updated System Information
    if [ -f /opt/seagate/eos/sspl/sspl_test/conf/sspl_tests.conf ]; then

        # append above parsed key-value pairs in sspl_tests.conf under
        # [SYSTEM_INFORMATION] section
        sed -i 's/node_id=000/node_id='"$node_id"'/g' /opt/seagate/eos/sspl/sspl_test/conf/sspl_tests.conf
        sed -i 's/site_id=000/site_id='"$site_id"'/g' /opt/seagate/eos/sspl/sspl_test/conf/sspl_tests.conf
        sed -i 's/rack_id=000/rack_id='"$rack_id"'/g' /opt/seagate/eos/sspl/sspl_test/conf/sspl_tests.conf
        sed -i 's/cluster_id=000/cluster_id='"$cluster_id"'/g' /opt/seagate/eos/sspl/sspl_test/conf/sspl_tests.conf

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
        port=$(sed -n -e '/primary_controller_port/ s/.*\= *//p' /etc/sspl.conf)
        if [ "$port" == "$MOCK_SERVER_PORT" ]
        then
            sed -i 's/primary_controller_port='"$MOCK_SERVER_PORT"'/primary_controller_port='"$primary_port"'/g' /etc/sspl.conf
        fi
    else
        port=$(/opt/seagate/eos/hare/bin/consul kv get sspl.STORAGE_ENCLOSURE.primary_controller_port)
        if [ "$port" == "$MOCK_SERVER_PORT" ]
        then
            /opt/seagate/eos/hare/bin/consul kv put sspl.STORAGE_ENCLOSURE.primary_controller_port $primary_port
        fi
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

    # Restore /opt/seagate/eos/hare/bin/consul data
    /opt/seagate/eos/hare/bin/consul kv delete -recurse var/eos/sspl/data
    /opt/seagate/eos/hare/bin/consul kv import @/tmp/consul_backup.json
    $sudo rm -f /tmp/consul_backup.json
}

cleanup()
{
    restore_cfg_services

    # Removing updated system information from sspl_tests.conf
    # This is required otherwise, everytime if we run sanity, key-value
    # pairs will be appended which will break the sanity.
    # Also, everytime, updated values from /etc/sspl.conf should be updated.
    sed -i 's/node_id='"$node_id"'/node_id=000/g' /opt/seagate/eos/sspl/sspl_test/conf/sspl_tests.conf
    sed -i 's/rack_id='"$rack_id"'/rack_id=000/g' /opt/seagate/eos/sspl/sspl_test/conf/sspl_tests.conf
    sed -i 's/site_id='"$site_id"'/site_id=000/g' /opt/seagate/eos/sspl/sspl_test/conf/sspl_tests.conf
    sed -i 's/cluster_id='"$cluster_id"'/cluster_id=000/g' /opt/seagate/eos/sspl/sspl_test/conf/sspl_tests.conf
    echo "Exiting..."
    exit 1
}

trap cleanup 1 2 3 6 9 15

execute_test()
{
    $sudo $script_dir/run_sspl-ll_tests.sh $*
}

flask_installed=$(python3.6 -c 'import pkgutil; print(1 if pkgutil.find_loader("flask") else 0)')
[ $flask_installed = "1" ] && [ $(python3.6 -c 'import flask; print(flask.__version__)') = "1.1.1" ] || {
    flask_help
    echo "Please install Flask 1.1.1 using
          pip3.6 install flask==1.1.1"
    echo -e "\n"
    exit 1
}

# Take backup of original sspl.conf
[[ -f /etc/sspl.conf ]] && $sudo cp /etc/sspl.conf /etc/sspl.conf.back

# check the port configured in consul
# change the port to $MOCK_SERVER_PORT as mock_server runs on $MOCK_SERVER_PORT
if [ "$SSPL_STORE_TYPE" == "consul" ]
then
    primary_port=$(/opt/seagate/eos/hare/bin/consul kv get sspl.STORAGE_ENCLOSURE.primary_controller_port)
    if [ "$primary_port" != "$MOCK_SERVER_PORT" ]
    then
        /opt/seagate/eos/hare/bin/consul kv put sspl.STORAGE_ENCLOSURE.primary_controller_port $MOCK_SERVER_PORT
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
    transmit_interval=$(/opt/seagate/eos/hare/bin/consul kv get sspl.NODEDATAMSGHANDLER.transmit_interval)
    disk_usage_threshold=$(/opt/seagate/eos/hare/bin/consul kv get sspl.NODEDATAMSGHANDLER.disk_usage_threshold)
    host_memory_usage_threshold=$(/opt/seagate/eos/hare/bin/consul kv get sspl.NODEDATAMSGHANDLER.host_memory_usage_threshold)
    cpu_usage_threshold=$(/opt/seagate/eos/hare/bin/consul kv get sspl.NODEDATAMSGHANDLER.cpu_usage_threshold)
else
    transmit_interval=$(sed -n -e '/transmit_interval/ s/.*\= *//p' /etc/sspl.conf)
    disk_usage_threshold=$(sed -n -e '/disk_usage_threshold/ s/.*\= *//p' /etc/sspl.conf)
    host_memory_usage_threshold=$(sed -n -e '/host_memory_usage_threshold/ s/.*\= *//p' /etc/sspl.conf)
    cpu_usage_threshold=$(sed -n -e '/cpu_usage_threshold/ s/.*\= *//p' /etc/sspl.conf)
fi

# setting values for testing
disk_out=`python3.6 -c "import psutil; print(int(psutil.disk_usage('/')[3]-2))"`
$sudo $script_dir/set_threshold.sh "10" $disk_out "0" "0"

echo "Restarting SSPL"
$sudo systemctl restart sspl-ll
echo "Waiting for SSPL to complete initialization of all the plugins"
$script_dir/rabbitmq_start_checker sspl-out actuator-resp-key
echo "Initialization completed. Starting tests"

# Switch SSPL to active state to resume all the suspended plugins. If SSPL is
# not switched to active state then plugins will not respond and tests will
# fail. Sending SIGUP to SSPL makes SSPL to read state file and switch state.
echo "state=active" > /var/eos/sspl/data/state.txt
PID=`ps -aux| grep "sspl_ll_d" | grep -v "grep" | awk '{print $2}'`
kill -s SIGHUP $PID

# Start tests
execute_test $*
retcode=$?

# Restoring original cache data
$sudo find /var/eos/sspl -maxdepth 2 -type d -path '/var/eos/sspl/data/*' -not -name 'iem'  -exec bash -c 'rm -rf ${0}' {} \;
$sudo find /var/eos/sspl -maxdepth 2 -type d -path '/var/eos/sspl/orig-data/*' -not -name 'iem'  -exec bash -c 'mv -f ${0} ${0/orig-data/data}/' {} \;
if [ -f /var/eos/sspl/orig-data/iem/last_processed_msg_time ]; then
    $sudo mv /var/eos/sspl/orig-data/iem/last_processed_msg_time /var/eos/sspl/data/iem/last_processed_msg_time
fi
$sudo rm -rf /var/eos/sspl/orig-data

# setting back the actual values
$sudo $script_dir/set_threshold.sh $transmit_interval $disk_usage_threshold $host_memory_usage_threshold $cpu_usage_threshold
[[ -f /etc/sspl.conf.back ]] && $sudo mv /etc/sspl.conf.back /etc/sspl.conf

echo "Tests completed, restored configs and services .."
restore_cfg_services

# Removing updated system information from sspl_tests.conf
# This is required otherwise, everytime if we run sanity, key-value
# pairs will be appended which will break the sanity.
# Also, everytime, updated values from /etc/sspl.conf should be updated.
sed -i 's/node_id='"$node_id"'/node_id=000/g' /opt/seagate/eos/sspl/sspl_test/conf/sspl_tests.conf
sed -i 's/rack_id='"$rack_id"'/rack_id=000/g' /opt/seagate/eos/sspl/sspl_test/conf/sspl_tests.conf
sed -i 's/site_id='"$site_id"'/site_id=000/g' /opt/seagate/eos/sspl/sspl_test/conf/sspl_tests.conf
sed -i 's/cluster_id='"$cluster_id"'/cluster_id=000/g' /opt/seagate/eos/sspl/sspl_test/conf/sspl_tests.conf


echo "Cleaned Up .."
exit $retcode
