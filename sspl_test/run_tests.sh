#!/bin/bash -e

# sspl-tests are to be performed with this script, which exits with 0 on success and 1 on failure.
#	Execute this test script
#	  run_tests.sh <role>.
#   <role> test - default. Execute set of QA tests.
#   <role> dev - Executes container based tests, takes sspl_install_path as an optional argument
#
####################################################################################
# TODO
# 1. Separate the LXC and lettuce, so that lettuce can be invoked separately.

[[ $EUID -ne 0 ]] && sudo=sudo
script_dir=$(dirname $0)
Usage()
{
    echo "Usage:
    $0 [role] [sspl_install_path]
where:
    role - {dev|test}. Default is 'test'.
    sspl_install_path - Path where sspl will be configured on the target. Default is '/root'. Only applicable for dev env"
    exit 1
}

role=${1:-test}
sspl_install_path=${2:-/root}

case $role in
"dev")
    $sudo $script_dir/run_dev_test.sh $sspl_install_path
    ;;
"test")
    $sudo $script_dir/run_qa_test.sh $2
    ;;
*)
    echo "Unknown role supplied"
    Usage
    exit 1
    ;;
esac
retcode=$?
exit $retcode
