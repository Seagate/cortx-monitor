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
source $script_dir/constants.sh
export PYTHONPATH=$script_dir/../..:$script_dir/../../low-level
# Default test plan is sanity
PLAN=${1:-sanity}

# Decide the test plan
IS_VIRTUAL=$(facter is_virtual)
if [ "$IS_VIRTUAL" != "true" ]
then
    # Find the nodename
    SRVNODE="$(sudo salt-call grains.get id --output=newline_values_only)"
    if [ -z "$SRVNODE" ];then
        SRVNODE="$(cat /etc/salt/minion_id)"
        if [ -z "$SRVNODE" ];then
            SRVNODE="srvnode-1"
        fi
    fi
    # Get the primary node
    PRIMARY="$(pcs status | grep 'Masters')"
    # Check if current node is primary
    if [[ "$PRIMARY" == *"$SRVNODE"* ]]
    then
        PLAN="self_primary"
    else
        PLAN="self_secondary"
    fi
fi

systemctl start crond

# Execute tests
sudo /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/run_test.py -t $script_dir/plans/$PLAN.pln
