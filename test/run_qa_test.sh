#!/bin/bash -e

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

MOCK_SERVER_PORT=28200

[[ $EUID -ne 0 ]] && sudo=sudo
script_dir=$(dirname $0)

flask_help()
{
 echo "Check if prior Flask version was installed using yum
       rpm -qa | grep python-flask"
 echo "If packge detail appears, uninstall Flask using command
       yum remove python-flask"
 echo "If package details doesn't appear, then it was installed using pip"
 echo "You can check Flask version using pip with following command
       pip freeze | grep Flask"
 echo "Uninstall previously installed Flask version using
       pip uninstall Flask"
 echo -e "In a similar way, uninstall all its dependencies using pip:
          pip uninstall Werkzeug
          pip uninstall Jinja2
          pip uninstall itsdangerous"
}

pre_requisites()
{
    # Backing up original persistence data
    $sudo rm -rf /var/cortx/sspl/orig-data
    $sudo mv /var/cortx/sspl/data /var/cortx/sspl/orig-data

    # Need empty persitence cache dir
    $sudo mkdir -p /var/cortx/sspl/data

    if [ -f "/var/cortx/sspl/orig-data/iem" ]; then
        $sudo cp /var/cortx/sspl/orig-data/iem /var/cortx/sspl/data/iem
    fi
}

kill_mock_server()
{
    # Kill mock API server
    pkill -f \./mock_server
}

cleanup()
{
    deleteMockedInterface
    # Again Changing port to default which is 80
    port=$(sed -n -e '/primary_controller_port/ s/.*\= *//p' /etc/sspl.conf)
    if [ $port == "$MOCK_SERVER_PORT" ]
    then
        sed -i 's/primary_controller_port='"$MOCK_SERVER_PORT"'/primary_controller_port=80/g' /etc/sspl.conf
    fi

    echo "Stopping mock server"
    kill_mock_server

    echo "Exiting..."
    exit 1
}

trap cleanup 0 1 2 3 6 9 15

execute_test()
{
    $sudo $script_dir/automated/run_sspl-ll_tests.sh
}

lettuce_version=$(pip list 2>/dev/null | grep -wi lettuce | awk '{print $2}')
[ ! -z $lettuce_version ] && [ $lettuce_version = "0.2.23" ] || {
    echo "Please install lettuce 0.2.23"
    exit 1
}

flask_version=$(pip list 2>/dev/null | grep -wi flask | awk '{print $2}')
[ ! -z $flask_version ] && [ $flask_version = "1.1.1" ] || {
    flask_help
    echo "Please install Flask 1.1.1 using
          pip install Flask==1.1.1"
    echo -e "\n"
    exit 1
}

# check the port configured in /etc/sspl.conf
# change the port to $MOCK_SERVER_PORT as mock_server runs on $MOCK_SERVER_PORT
port=$(sed -n -e '/primary_controller_port/ s/.*\= *//p' /etc/sspl.conf)
if [ $port == "80" ]
then
    sed -i 's/primary_controller_port=80/primary_controller_port='"$MOCK_SERVER_PORT"'/g' /etc/sspl.conf
fi

# Setting pre-requisites first
pre_requisites

# Start mock API server
echo "Starting mock server on 127.0.0.1:$MOCK_SERVER_PORT"
$script_dir/mock_server &

deleteMockedInterface()
{
    ip link delete eth-mocked
    ip link delete br0
}

# IMP NOTE: Please make sure that SSPL conf file has
# primary_controller_ip=127.0.0.1 and primary_controller_port=$MOCK_SERVER_PORT.
# For sanity test SSPL should connect to mock server instead of real server.
# Restart SSPL to re-read configuration
#Taking the backup of /etc/sspl.conf before running test cases and place back as it is after test.
#for testing purpose need to generating the alerts for CPU usage, Memory Usage and disk usage the
#making the threshold value less than the actual usage for HOst, CPU and DIsk we update the the
#threshold values (e.g. # Disk Usage Threshold value in terms of usage percentage (i.e. 0 to 100)
#disk_usage_threshold=28
# CPU Usage Threshold value in terms of usage in percentage (i.e. 0 to 100%)
#cpu_usage_threshold=1
# Memory Usage Threshold value in terms of usage in percentage (i.e. 0 to 100%)
#host_memory_usage_threshold=34.3)
$sudo cp /etc/sspl.conf /etc/sspl.conf.back
$sudo $script_dir/set_threshold.sh
echo "Restarting SSPL"
systemctl restart sspl.service
echo "Waiting for SSPL to complete initialization of all the plugins"
$script_dir/rabbitmq_start_checker sspl-out actuator-resp-key
echo "Initialization completed. Starting tests"

# Start tests
execute_test
retcode=$?

#Updating the /etc/sspl.conf with respect to there original changes.
$sudo mv /etc/sspl.conf.back /etc/sspl.conf

# Restoring original cache data
$sudo rm -rf /var/cortx/sspl/data
$sudo mv /var/cortx/sspl/orig-data /var/cortx/sspl/data

exit $retcode
