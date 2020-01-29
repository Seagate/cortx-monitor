#!/bin/bash -e

MOCK_SERVER_PORT=5100

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
    $sudo rm -rf /var/sspl/orig-data
    $sudo mkdir -p /var/sspl/orig-data
    $sudo find /var/sspl -maxdepth 2 -type d -path '/var/sspl/data/*' -not -name 'iem'  -exec bash -c 'mv -f ${0} ${0/data/orig-data}/' {} \;
    $sudo mkdir -p /var/sspl/orig-data/iem
    if [ -f /var/sspl/data/iem/last_processed_msg_time ]; then
        $sudo mv /var/sspl/data/iem/last_processed_msg_time /var/sspl/orig-data/iem/last_processed_msg_time
    fi
}

deleteMockedInterface()
{
    ip link show eth-mocked
    if [ $? == 0 ]
    then
        ip link delete eth-mocked
    fi
}

kill_mock_server()
{
    # Kill mock API server
    pkill -f \./mock_server
}

cleanup()
{
    # Again Changing port to default which is 80
    port=$(sed -n -e '/primary_controller_port/ s/.*\= *//p' /etc/sspl.conf)
    if [ $port == "$MOCK_SERVER_PORT" ]
    then
        sed -i 's/primary_controller_port='"$MOCK_SERVER_PORT"'/primary_controller_port='"$primary_port"'/g' /etc/sspl.conf
    fi

    echo "Stopping mock server"
    kill_mock_server
    deleteMockedInterface
    echo "Exiting..."
    exit 1
}

trap cleanup 0 1 2 3 6 9 15

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
$sudo cp /etc/sspl.conf /etc/sspl.conf.back



# check the port configured in /etc/sspl.conf
# change the port to $MOCK_SERVER_PORT as mock_server runs on $MOCK_SERVER_PORT
primary_port=$(sed -n -e '/primary_controller_port/ s/.*\= *//p' /etc/sspl.conf)
if [ "$primary_port" != "$MOCK_SERVER_PORT" ]
then
    sed -i 's/primary_controller_port='"$primary_port"'/primary_controller_port='"$MOCK_SERVER_PORT"'/g' /etc/sspl.conf
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

$sudo $script_dir/set_threshold.sh
echo "Restarting SSPL"
$sudo systemctl restart sspl-ll
echo "Waiting for SSPL to complete initialization of all the plugins"
$script_dir/rabbitmq_start_checker sspl-out actuator-resp-key
echo "Initialization completed. Starting tests"

# Switch SSPL to active state to resume all the suspended plugins. If SSPL is
# not switched to active state then plugins will not respond and tests will
# fail. Sending SIGUP to SSPL makes SSPL to read state file and switch state.
echo "state=active" > /var/sspl/data/state.txt
PID=`ps -aux| grep "sspl_ll_d -c /etc/sspl.conf" | grep -v "grep" | awk '{print $2}'`
kill -s SIGHUP $PID

# Start tests
execute_test $*
retcode=$?

# Restoring original cache data
$sudo find /var/sspl -maxdepth 2 -type d -path '/var/sspl/data/*' -not -name 'iem'  -exec bash -c 'rm -rf ${0}' {} \;
$sudo find /var/sspl -maxdepth 2 -type d -path '/var/sspl/orig-data/*' -not -name 'iem'  -exec bash -c 'mv -f ${0} ${0/orig-data/data}/' {} \;
if [ -f /var/sspl/orig-data/iem/last_processed_msg_time ]; then
    $sudo mv /var/sspl/orig-data/iem/last_processed_msg_time /var/sspl/data/iem/last_processed_msg_time
fi
$sudo rm -rf /var/sspl/orig-data

$sudo mv /etc/sspl.conf.back /etc/sspl.conf
echo "Tests completed, restored configs .."
cleanup
echo "Cleaned Up .."
exit $retcode
