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
source "$script_dir"/constants.sh
# Default test plan is sanity
PLAN=${1:-sanity}

SRVNODE=""

# Decide the test plan
IS_VIRTUAL=$(facter is_virtual)
if [ "$IS_VIRTUAL" != "true" ]
then
    # Find the nodename
    # Onward LDR_R2, consul and salt will be abstracted out and
    # won't exist as hard dependencies of SSPL
    if [ "$PRODUCT_NAME" == "LDR_R1" ]; then
        SRVNODE="$(sudo salt-call grains.get id --output=newline_values_only)"
        [ -z "$SRVNODE" ] && SRVNODE="$(consul kv get system_information/salt_minion_id)"
        if [ -z "$SRVNODE" ];then
            SRVNODE="$(cat /etc/salt/minion_id)"
        fi
        [ -z "$SRVNODE" ] && SRVNODE="srvnode-1"

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
    [ -z "$PLAN" ] && PLAN="self_primary"
fi

systemctl start crond

# Execute tests
sudo /opt/seagate/"$PRODUCT_FAMILY"/sspl/sspl_test/run_test.py -t "$script_dir"/plans/"$PLAN".pln
