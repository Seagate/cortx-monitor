#!/bin/bash -e

[[ $EUID -ne 0 ]] && sudo=sudo
script_dir=$(dirname $0)
execute_test()
{
    $sudo $script_dir/automated/run_sspl-ll_tests.sh
}

lettuce_version=$(pip list 2> /dev/null | grep -w lettuce | cut -c30- || echo)
[ ! -z $lettuce_version ] && [ $lettuce_version = "0.2.23" ] || {
    echo "Please install lettuce 0.2.23"
    exit 1
}
execute_test
retcode=$?
exit $retcode
