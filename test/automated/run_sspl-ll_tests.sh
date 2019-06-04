#!/bin/bash -e

echo "Running Automated Integration Tests for SSPL-LL"
script_dir=$(dirname $0)
export PYTHONPATH=$script_dir/../..:$script_dir/../../low-level

# Create simulated disk manager data
# TODO: Remove this line. This file is not needed as it is used for a deprecated module
# called "drive_manager"
# cp ../../../installation/deps/drive_manager.json /tmp/dcs/drivemanager
# Disabling for EES-non-requirement
# chown -R zabbix:zabbix /tmp/dcs

systemctl start crond

if [[ -f ./lettucetests.xml ]]; then
	rm ./lettucetests.xml
fi

# Locate features directory
BASE_DIR=$(realpath $(dirname $0)/)

# Execute tests and save results
lettuce --with-xunit --xunit-file=lettucetests.xml --verbosity=4 $BASE_DIR

# Search results for success
success=`grep 'testsuite errors="0" failures="0"' lettucetests.xml`
if [[ "$success" == "" ]]; then
	exit 1
else
	exit 0
fi

