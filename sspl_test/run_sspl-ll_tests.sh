#!/bin/bash -e

echo "Running Automated Integration Tests for SSPL-LL"
script_dir=$(dirname $0)
export PYTHONPATH=$script_dir/../..:$script_dir/../../low-level
PLAN=${1:-sanity}

systemctl start crond

# Execute tests
$sudo python $script_dir/run_test.py -t $script_dir/plans/$PLAN.pln
