#!/bin/bash -e
echo "Running Automated Integration Tests for SSPL-LL"
script_dir=$(dirname $0)
. $script_dir/constants.sh
export PYTHONPATH=$script_dir/../..:$script_dir/../../low-level
PLAN=${1:-sanity}

IS_VIRTUAL=$(facter is_virtual)
if [ "$IS_VIRTUAL" != "true" ]
then
    PLAN="self"
    # clean up test files from previous run
    rm -f /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/self_hw_bmc_error.txt
fi

systemctl start crond

# Execute tests
#$sudo ./$script_dir/run_test.py -t $script_dir/plans/$PLAN.pln
sudo /opt/seagate/$PRODUCT_FAMILY/sspl/sspl_test/lib/sspl_tests -t $script_dir/plans/$PLAN.pln
