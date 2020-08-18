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


echo "Running Automated Integration Tests for SSPL-LL"
script_dir=$(dirname $0)
export PYTHONPATH=$script_dir/../..:$script_dir/../../low-level

# Create simulated disk manager data
# TODO: Remove this line. This file is not needed as it is used for a deprecated module
# called "drive_manager"
# cp ../../../installation/deps/drive_manager.json /tmp/dcs/drivemanager
# Disabling for LDR_R1-non-requirement
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

