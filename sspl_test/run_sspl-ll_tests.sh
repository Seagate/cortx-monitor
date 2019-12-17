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

# Execute tests
$sudo python $script_dir/run_test.py -t $script_dir/plans/alerts.pln
