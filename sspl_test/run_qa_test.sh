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
IS_VIRTUAL=$(facter is_virtual)

[[ $EUID -ne 0 ]] && sudo=sudo
script_dir=$(dirname $0)
source $script_dir/constants.sh
SSPL_STORE_TYPE=confstor

coverage_enabled="False"
while [ $# -gt 0 ]; do
    case $1 in
        --plan )
            declare plan="$2"
            ;;
        --coverage )
            declare coverage_enabled="$2"
            ;;
        * ) ;;
    esac
    shift
done

sspl_config=yaml://$SSPL_CONFIG_FILE
sspl_test_config=yaml://$SSPL_TEST_CONFIG_FILE
global_config_url=`conf $sspl_config get "SYSTEM_INFORMATION>global_config_copy_url"`
global_config=$(echo $global_config_url | tr -d "["\" | tr -d "\"]")

machine_id=`cat /etc/machine-id`
DATA_PATH="/var/$PRODUCT_FAMILY/sspl/data/"

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
    if [ "$IS_VIRTUAL" == "true" ]
    then
        # Backing up original persistence data
        $sudo rm -rf /var/$PRODUCT_FAMILY/sspl/orig-data
        $sudo mkdir -p /var/$PRODUCT_FAMILY/sspl/orig-data
        $sudo find "/var/$PRODUCT_FAMILY/sspl" -maxdepth 2 \
            -type d -path "/var/$PRODUCT_FAMILY/sspl/data/*" \
            -not \( -name 'iem' -o  -name 'coverage' \)  \
            -exec bash -c 'mv -f ${0} ${0/data/orig-data}/' {} \;
        $sudo mkdir -p /var/$PRODUCT_FAMILY/sspl/orig-data/iem
        if [ -f /var/$PRODUCT_FAMILY/sspl/data/iem/last_processed_msg_time ]; then
            $sudo mv /var/$PRODUCT_FAMILY/sspl/data/iem/last_processed_msg_time /var/$PRODUCT_FAMILY/sspl/orig-data/iem/last_processed_msg_time
        fi

        # Enable ipmi simulator
        cp -Rp $script_dir/ipmi_simulator/ipmisimtool /usr/bin
        mkdir -p "$DATA_PATH/server/"
        chown -R sspl-ll:sspl-ll "$DATA_PATH/server/"
        chmod 755 "$DATA_PATH/server/"
        touch "$DATA_PATH/server/activate_ipmisimtool"
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
    # call reset env script for coverage if coverage is enabled.
    if [ "$coverage_enabled" == "True" ]
    then
        $sudo python3 "$script_dir/coverage/coverage_setup.py" stop
    fi

    # clear the dummy_service configurations made for
    # alerts.os.test_service_monitor_sensor test
    service_name=dummy_service.service
    service_executable_code_des=/var/cortx/sspl/test
    $sudo systemctl stop $service_name
    $sudo systemctl disable $service_name
    $sudo rm -rf $service_executable_code_des/dummy_service.py
    $sudo rm -rf /etc/systemd/system/$service_name
    $sudo systemctl daemon-reload
    # Restoring MC port to value stored before tests
    if [ "$SSPL_STORE_TYPE" == "file" ]
    then
        port=$(sed -n -e '/primary_controller_port/ s/.*\: *//p' $SSPL_CONFIG_FILE)
        if [ "$port" == "$MOCK_SERVER_PORT" ]
        then
            sed -i 's/primary_controller_ip: '"$MOCK_SERVER_IP"'/primary_controller_ip: '"$primary_ip"'/g' $SSPL_CONFIG_FILE
            sed -i 's/primary_controller_port: '"$MOCK_SERVER_PORT"'/primary_controller_port: '"$primary_port"'/g' $SSPL_CONFIG_FILE
        fi
        # Removing updated system information from sspl_tests.conf
        # This is required otherwise, everytime if we run sanity, key-value
        # pairs will be appended which will break the sanity.
        # Also, everytime, updated values from /etc/sspl.conf should be updated.
        sed -i "s/node_id: $node_id/node_id: SN01/g" /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.conf
        sed -i "s/rack_id: $rack_id/rack_id: RC01/g" /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.conf
        sed -i "s/site_id: $site_id/site_id: DC01/g" /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.conf
        sed -i "s/cluster_id: $cluster_id/cluster_id: CC01/g" /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.conf
    elif [ "$SSPL_STORE_TYPE" == "confstor" ]
    then
        port=$(conf $global_config get "storage>$encl_id>controller>primary>port")
        port=$(echo $port | tr -d "["\" | tr -d "\"]")
        if [ "$port" == "$MOCK_SERVER_PORT" ]
        # TODO: Avoid set on global config, need to change this before
        # provisioner gives common backend
        then
            conf $global_config set "storage_enclosure>$encl_id>controller>primary>port=$primary_port"
            conf $global_config set "storage_enclosure>$encl_id>controller>primary>ip=$primary_ip"
        fi
        conf "$global_config" set "server_node>$machine_id>node_id=SN01"
        conf "$global_config" set "server_node>$machine_id>site_id=DC01"
        conf "$global_config" set "server_node>$machine_id>rack_id=RC01"
        conf "$global_config" set "server_node>$machine_id>cluster_id=CC01"
    fi

    if [ "$IS_VIRTUAL" == "true" ]
    then
        echo "Stopping mock server"
        kill_mock_server
        deleteMockedInterface
    fi

    # Remove ipmisimtool
    rm -f /usr/bin/ipmisimtool
    rm -f "$DATA_PATH/server/activate_ipmisimtool"
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

if [ "$plan" == "sanity" ]
then
    if [ "$IS_VIRTUAL" == "true" ]
    then
    echo "VM detected."
    echo "ERROR: $plan is intended to run on hardware setup."
    exit 1
    fi
fi

if [ "$SSPL_STORE_TYPE" == "confstor" ]
then
    # Read common key which are needed to fetch confstor config.
    encl_id=`conf $global_config get "server_node>$machine_id>storage>enclosure_id"`
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
[[ -f $SSPL_CONFIG_FILE ]] && $sudo cp $SSPL_CONFIG_FILE ${SSPL_CONFIG_FILE}.back
#[[ -f $test_config_file ]] && $sudo cp $test_config_file ${test_config_file}.back
[[ -f $global_config_file ]] && $sudo cp $global_config_file ${global_config_file}.back

# check the port configured
# if virtual machine, change the port to $MOCK_SERVER_PORT as mock_server runs on $MOCK_SERVER_PORT
if [ "$SSPL_STORE_TYPE" == "confstor" ]
then
    primary_ip=`conf $global_config get "storage_enclosure>$encl_id>controller>primary>ip"`
    primary_ip=$(echo $primary_ip | tr -d "["\" | tr -d "\"]")
    primary_port=`conf $global_config get "storage_enclosure>$encl_id>controller>primary>port"`
    primary_port=$(echo $primary_port | tr -d "["\" | tr -d "\"]")
    if [ "$IS_VIRTUAL" == "true" ]
    then
        if [ "$primary_port" != "$MOCK_SERVER_PORT" ]
        then
            conf $global_config set "storage_enclosure>$encl_id>controller>primary>port=$MOCK_SERVER_PORT"
            conf $global_config set "storage_enclosure>$encl_id>controller>primary>ip=$MOCK_SERVER_IP"
        fi
    fi
else
    primary_ip=$(sed -n -e '/primary_controller_ip/ s/.*\: *//p' $SSPL_CONFIG_FILE)
    primary_port=$(sed -n -e '/primary_controller_port/ s/.*\: *//p' $SSPL_CONFIG_FILE)
    if [ "$IS_VIRTUAL" == "true" ]
    then
        if [ "$primary_port" != "$MOCK_SERVER_PORT" ]
        then
            sed -i 's/primary_controller_ip: '"$primary_ip"'/primary_controller_ip: '"$MOCK_SERVER_IP"'/g' $SSPL_CONFIG_FILE
            sed -i 's/primary_controller_port: '"$primary_port"'/primary_controller_port: '"$MOCK_SERVER_PORT"'/g' $SSPL_CONFIG_FILE
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
# For dev_sanity test SSPL should connect to mock server instead of real server (for vm)
# Restart SSPL to re-read configuration
if [ "$SSPL_STORE_TYPE" == "confstor" ]
then
    transmit_interval=`conf $sspl_config get "NODEDATAMSGHANDLER>transmit_interval"`
    transmit_interval=$(echo $transmit_interval | tr -d "["\" | tr -d "\"]")
    disk_usage_threshold=`conf $sspl_config get "NODEDATAMSGHANDLER>disk_usage_threshold"`
    disk_usage_threshold=$(echo $disk_usage_threshold | tr -d "["\" | tr -d "\"]")
    host_memory_usage_threshold=`conf $sspl_config get "NODEDATAMSGHANDLER>host_memory_usage_threshold"`
    host_memory_usage_threshold=$(echo $host_memory_usage_threshold| tr -d "["\" | tr -d "\"]")
    cpu_usage_threshold=`conf $sspl_config get "NODEDATAMSGHANDLER>cpu_usage_threshold"`
    cpu_usage_threshold=$(echo $cpu_usage_threshold | tr -d "["\" | tr -d "\"]")
    node_id=`conf $global_config get "server_node>$machine_id>node_id"`
    node_id=$(echo $node_id | tr -d "["\" | tr -d "\"]")
    site_id=`conf $global_config get "server_node>$machine_id>site_id"`
    site_id=$(echo $site_id | tr -d "["\" | tr -d "\"]")
    rack_id=`conf $global_config get "server_node>$machine_id>rack_id"`
    rack_id=$(echo $rack_id | tr -d "["\" | tr -d "\"]")
    cluster_id=`conf $global_config get "server_node>$machine_id>cluster_id"`
    cluster_id=$(echo $cluster_id | tr -d "["\" | tr -d "\"]")
    primary_controller_ip=`conf $global_config get "storage_enclosure>$encl_id>controller>primary>ip"`
    primary_controller_ip=$(echo $primary_controller_ip | tr -d "["\" | tr -d "\"]")
else
    transmit_interval=$(sed -n -e '/transmit_interval/ s/.*\: *//p' $SSPL_CONFIG_FILE)
    disk_usage_threshold=$(sed -n -e '/disk_usage_threshold/ s/.*\: *//p' $SSPL_CONFIG_FILE)
    host_memory_usage_threshold=$(sed -n -e '/host_memory_usage_threshold/ s/.*\: *//p' $SSPL_CONFIG_FILE)
    cpu_usage_threshold=$(sed -n -e '/cpu_usage_threshold/ s/.*\: *//p' $SSPL_CONFIG_FILE)
    rack_id=$(sed -n -e '/rack_id/ s/.*\: *//p' $SSPL_CONFIG_FILE)
    site_id=$(sed -n -e '/site_id/ s/.*\: *//p' $SSPL_CONFIG_FILE)
    node_id=$(sed -n -e '/node_id/ s/.*\: *//p' $SSPL_CONFIG_FILE)
    cluster_id=$(sed -n -e '/cluster_id/ s/.*\: *//p' $SSPL_CONFIG_FILE)
    cluster_nodes=$(sed -n -e '/cluster_nodes/ s/.*\: *//p' $SSPL_CONFIG_FILE)
    primary_controller_ip=$(sed -n -e '/primary_controller_ip/ s/.*\: *//p' $SSPL_CONFIG_FILE)
fi

# setting values for testing
if [ "$IS_VIRTUAL" == "true" ]
then
    disk_out=`python3.6 -c "import psutil; print(int(psutil.disk_usage('/')[3]-2))"`
    $sudo $script_dir/set_threshold.sh "10" $disk_out "0" "0" $sspl_config
fi

if [ "$SSPL_STORE_TYPE" == "confstor" ]
then
    conf $global_config set "server_node>$machine_id>node_id=$node_id"
    conf $global_config set "server_node>$machine_id>site_id=$site_id"
    conf $global_config set "server_node>$machine_id>rack_id=$rack_id"
    conf $global_config set "server_node>$machine_id>cluster_id=$cluster_id"
else
    # Update sspl_tests.conf with updated System Information
    # append above parsed key-value pairs in sspl_tests.conf under [SYSTEM_INFORMATION] section
    sed -i 's/node_id: .*/node_id: '"$node_id"'/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.conf
    sed -i 's/site_id: 001/site_id: '"$site_id"'/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.conf
    sed -i 's/rack_id: 001/rack_id: '"$rack_id"'/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.conf
    sed -i 's/cluster_id: .*/cluster_id: '"$cluster_id"'/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.conf
    sed -i 's/cluster_nodes: localhost/cluster_nodes: '"$cluster_nodes"'/g' /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/conf/sspl_tests.conf
fi

if [ "$IS_VIRTUAL" == "true" ]
then
    echo "Stoping the SSPL service"
    $sudo systemctl stop sspl.service
    echo "Code Coverage enabled : $coverage_enabled"
    if [ "$coverage_enabled" == "True" ]
    then
        $sudo python3 "$script_dir/coverage/coverage_setup.py" start
    fi
    # consume all alerts before SSPL restarts. So sspl_start_checker
    # waits till SSPL initialized, if previous alerts are availble,
    # sspl_start_checker will use those and test cases will be executed
    # before SSPL initialization
    $script_dir/messaging/consume.py
    echo "Starting the SSPL service"
    $sudo systemctl start sspl.service
    sleep 5
    echo "Waiting for SSPL to complete initialization of all the plugins.."
    $script_dir/sspl_start_checker
fi

echo "Initialization completed. Starting tests"

# Switch SSPL to active state to resume all the suspended plugins. If SSPL is
# not switched to active state then plugins will not respond and tests will
# fail. Sending SIGUP to SSPL makes SSPL to read state file and switch state.
if [ "$IS_VIRTUAL" == "true" ]
then
    echo "state=active" > /var/$PRODUCT_FAMILY/sspl/data/state.txt
    PID=`/usr/bin/pgrep -d " " -f /opt/seagate/cortx/sspl/low-level/sspl_d`
    kill -s SIGHUP $PID
fi

# Start tests
execute_test $plan
retcode=$?

if [ "$IS_VIRTUAL" == "true" ]
then
    # Restoring original cache data
    $sudo find "/var/$PRODUCT_FAMILY/sspl" -maxdepth 2 \
        -type d -path "/var/$PRODUCT_FAMILY/sspl/data/*" \
        -not \( -name 'iem' -o  -name 'coverage' \) \
        -exec bash -c 'rm -rf ${0}' {} \;

    $sudo find "/var/$PRODUCT_FAMILY/sspl" -maxdepth 2 \
        -type d -path "/var/$PRODUCT_FAMILY/sspl/orig-data/*" \
        -not \( -name 'iem' -o  -name 'coverage' \) \
        -exec bash -c 'mv -f ${0} ${0/orig-data/data}/' {} \;
    if [ -f /var/$PRODUCT_FAMILY/sspl/orig-data/iem/last_processed_msg_time ]; then
        $sudo mv /var/$PRODUCT_FAMILY/sspl/orig-data/iem/last_processed_msg_time /var/$PRODUCT_FAMILY/sspl/data/iem/last_processed_msg_time
    fi
    $sudo rm -rf /var/$PRODUCT_FAMILY/sspl/orig-data
fi

if [ "$IS_VIRTUAL" == "true" ]
then
    # setting back the actual values
    $sudo $script_dir/set_threshold.sh $transmit_interval $disk_usage_threshold $host_memory_usage_threshold $cpu_usage_threshold $sspl_config
fi
[[ -f ${SSPL_CONFIG_FILE}.back ]] && $sudo mv ${SSPL_CONFIG_FILE}.back $SSPL_CONFIG_FILE
#[[ -f ${test_config_file}.back ]] && $sudo mv ${test_config_file}.back $test_config_file
[[ -f ${global_config_file}.back ]] && $sudo mv ${global_config_file}.back $global_config_file

echo "Tests completed, restored configs and services .."
restore_cfg_services

echo "Cleaned Up .."
exit $retcode
