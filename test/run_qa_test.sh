#!/bin/bash -e

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
    $sudo mv /var/sspl/data /var/sspl/orig-data

    # Need empty persitence cache dir
    $sudo mkdir -p /var/sspl/data

    if [ -f "/var/sspl/orig-data/iem" ]; then
        $sudo cp /var/sspl/orig-data/iem /var/sspl/data/iem
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
    if [ $port == "8090" ]
    then
        sed -i 's/primary_controller_port=8090/primary_controller_port=80/g' /etc/sspl.conf
    fi

    echo "Stopping mock server"
    kill_mock_server
    echo "Exiting..."
    exit 1
}

trap cleanup 0 2 15

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
# change the port to 8090 as mock_server runs on 8090
port=$(sed -n -e '/primary_controller_port/ s/.*\= *//p' /etc/sspl.conf)
if [ $port == "80" ]
then
    sed -i 's/primary_controller_port=80/primary_controller_port=8090/g' /etc/sspl.conf
fi

# Setting pre-requisites first
pre_requisites

# Start mock API server
echo "Starting mock server on 127.0.0.1:8090"
$script_dir/mock_server &

# IMP NOTE: Please make sure that SSPL conf file has
# primary_controller_ip=127.0.0.1 and primary_controller_port=8090.
# For sanity test SSPL should connect to mock server instead of real server.
# Restart SSPL to re-read configuration
$sudo $script_dir/set_disk_threshold.sh
echo "Restarting SSPL"
systemctl restart sspl-ll
echo "Waiting for SSPL to complete initialization of all the plugins"
$script_dir/rabbitmq_start_checker sspl-out actuator-resp-key
echo "Initialization completed. Starting tests"

# Start tests
execute_test
retcode=$?

# Restoring original cache data
$sudo rm -rf /var/sspl/data
$sudo mv /var/sspl/orig-data /var/sspl/data

exit $retcode
