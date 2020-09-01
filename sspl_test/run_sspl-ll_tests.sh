#!/bin/bash -e
echo "Running Automated Integration Tests for SSPL-LL"
script_dir=$(dirname $0)
. $script_dir/constants.sh
export PYTHONPATH=$script_dir/../..:$script_dir/../../low-level
# Default test plan is sanity
PLAN=${1:-sanity}

# Decide the test plan
IS_VIRTUAL=$(facter is_virtual)
if [ "$IS_VIRTUAL" != "true" ]
then
    # Find the nodename
    SRVNODE="$(salt-call grains.get id --output=newline_values_only)"
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
#$sudo ./$script_dir/run_test.py -t $script_dir/plans/$PLAN.pln
sudo /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/lib/sspl_tests -t $script_dir/plans/$PLAN.pln
