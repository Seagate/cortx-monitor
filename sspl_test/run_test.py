#!/usr/bin/python3.6

# Copyright (c) 2018-2020 Seagate Technology LLC and/or its Affiliates
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


"""
 ****************************************************************************
  Description:       Initiates execution of all the tests

 ****************************************************************************
"""

import sys, os, time
import traceback
import errno
import re
import argparse

from generate_test_report import generate_html_report
from common import (TestFailed, init_rabbitMQ_msg_processors,
    stop_rabbitMQ_msg_processors)
from framework.utils.conf_utils import Conf, SSPL_TEST_CONF


skip_group_prefixes = {
    "REALSTORSENSORS": "alerts.realstor",
    "NODEHWSENSOR": "alerts.node",
    "SYSTEMDWATCHDOG": None,
    "RAIDSENSOR": None,
}

def conf_skipped_prefixes():
    for group in skip_group_prefixes.keys():
        monitor = Conf.get(SSPL_TEST_CONF,f"{group}>monitor", 'true')
        if monitor not in ['true', True]:
            yield skip_group_prefixes[group]

result = {}

def tmain(argp, argv):

    args = {}

    # Prepare to run the test, all or subset per command line args
    ts_list = []
    if argp.t is not None:
        if not os.path.exists(argp.t):
            raise TestFailed('Missing file %s' %argp.t)
        with open(argp.t) as f:
            content = f.readlines()
            ts_list = [x.strip() for x in content]
    else:
        file_path = os.path.dirname(os.path.realpath(__file__))
        for root, directories, filenames in os.walk(os.getcwd()):
            for filename in filenames:
                print("filename : {}".format(filename))
                if re.match(r'test_.*\.py$', filename):
                    file = os.path.join(root, filename).rsplit('.', 1)[0]\
                        .replace(file_path + "/", "").replace("/", ".")
                    ts_list.append(file)

    ts_count = test_count = pass_count = fail_count = skip_count = 0
    ts_start_time = time.time()

    skipped_prefixes = list(conf_skipped_prefixes())
    for ts in ts_list:
        print('\n####### Test Suite: %s ######' %ts)
        ts_count += 1
        if any( (ts.startswith(p) for p in skipped_prefixes if p is not None) ):
            skip_count += 1
            result.update({ts: {"Skip": 0}})
            print("%s: Skipped" % ts)
            continue

        try:
            ts_module = __import__(ts, fromlist=[ts])
            # Initialization
            init = getattr(ts_module, 'init')
            init(args)
        except Exception as e:
            print('FAILED: Error: %s #@#@#@' %e)
            fail_count += 1
            result.update({ts: {"Fail": 0}})
            continue

        # Actual test execution
        for test in ts_module.test_list:
            test_count += 1
            try:
                start_time = time.time()
                test(args)
                duration = time.time() - start_time
                print('%s:%s: PASSED (Time: %ds)' %(ts, test.__name__, duration))
                pass_count += 1
                result.update({ts: {"Pass": duration}})

            except (TestFailed, Exception) as e:
                print('%s:%s: FAILED #@#@#@' %(ts, test.__name__))
                print('    %s\n' %e)
                fail_count += 1
                result.update({ts: {"Fail": 0}})

    # View of consolidated test suite status
    print('\n', '*'*90)
    print('{:60} {:10} {:10}'.format("TestSuite", "Status", "Duration(secs)"))
    print('*'*90)
    for k,v in result.items():
        print('{:60} {:10} {:10}s'.format(k, list(v.keys())[0], int(list(v.values())[0])))

    duration = time.time() - ts_start_time
    print('\n****************************************************')
    print('TestSuite:%d Tests:%d Passed:%d Failed:%d Skipped:%d TimeTaken:%ds' \
        %(ts_count, test_count, pass_count, fail_count, skip_count, duration))
    print('******************************************************')

if __name__ == '__main__':
    try:
        argParser = argparse.ArgumentParser(
            usage = "%(prog)s [-h] [-t]",
            formatter_class = argparse.RawDescriptionHelpFormatter)
        argParser.add_argument("-t",
                help="Enter path of testlist file")
        args = argParser.parse_args()

        args = argParser.parse_args()
        init_rabbitMQ_msg_processors()
        tmain(args, sys.argv[0])
        generate_html_report(result)
        stop_rabbitMQ_msg_processors()
    except Exception as e:
        print(e, traceback.format_exc())
        stop_rabbitMQ_msg_processors()
