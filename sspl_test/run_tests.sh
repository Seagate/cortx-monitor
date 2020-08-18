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
    $0 [role] [plan] [avoid_rmq] [sspl_install_path]
where:
    role - {dev|test}. Default is 'test'.
    sspl_install_path - Path where sspl will be configured on the target. Default is '/root'. Only applicable for dev env"
    exit 1
}

role=${1:-test}
plan=${2:-sanity}
avoid_rmq=${3:-}
sspl_install_path=${4:-/root}

case $role in
"dev")
    $sudo $script_dir/run_dev_test.sh $sspl_install_path
    ;;
"test")
    $sudo $script_dir/run_qa_test.sh $plan $avoid_rmq
    ;;
*)
    echo "Unknown role supplied"
    Usage
    exit 1
    ;;
esac
retcode=$?
exit $retcode
