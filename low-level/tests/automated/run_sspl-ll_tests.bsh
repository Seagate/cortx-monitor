#!/bin/bash -e

echo "Running Automated Integration Tests for SSPL-LL"

# Create simulated disk manager data
mkdir -p /tmp/dcs/drivemanager
cp ../../../installation/deps/drive_manager.json /tmp/dcs/drivemanager
chown -R zabbix:zabbix /tmp/dcs
mkdir -p /tmp/dcs/hpi

systemctl start crond
systemctl restart sspl-ll

if [[ -f ./lettucetests.xml ]]; then
	rm ./lettucetests.xml
fi

# Execute tests and save results
lettuce --with-xunit --xunit-file=lettucetests.xml

# Search results for success
success=`grep 'testsuite errors="0" failures="0"' lettucetests.xml`
if [[ "$success" == "" ]]; then
	exit 1
else
	exit 0
fi

