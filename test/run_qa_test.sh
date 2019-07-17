#!/bin/bash -e

[[ $EUID -ne 0 ]] && sudo=sudo
script_dir=$(dirname $0)

kill_mock_server()
{
    # Kill mock API server
    pkill -f \./mock_server
}

cleanup()
{
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

lettuce_version=$(pip list 2> /dev/null | grep -w lettuce | cut -c30- || echo)
[ ! -z $lettuce_version ] && [ $lettuce_version = "0.2.23" ] || {
    echo "Please install lettuce 0.2.23"
    exit 1
}

# Start mock API server
echo "Starting mock server on 127.0.0.1:8090"
$script_dir/mock_server &

# IMP NOTE: Please make sure that SSPL conf file has
# primary_controller_ip=127.0.0.1 and primary_controller_port=8090.
# For sanity test SSPL should connect to mock server instead of real server.
# Restart SSPL to re-read configuration
echo "Restarting SSPL"
systemctl restart sspl-ll

# Start tests
execute_test

kill_mock_server

retcode=$?
exit $retcode
