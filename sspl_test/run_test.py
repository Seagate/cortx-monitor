#!/usr/bin/python3.6

"""
 ****************************************************************************
 Filename:          run_test.py
 Description:       Initiates execution of all the tests

 Creation Date:     22/06/2018
 Author:            Ujjwal Lanjewar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import sys, os, time
import traceback
import errno
import re
import argparse

# Adding sspl and sspl_test path
test_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(test_path))

from sspl_test.common import TestFailed, init_rabbitMQ_msg_processors, stop_rabbitMQ_msg_processors

def tmain(argp, argv):
    # Import required TEST modules
    ts_path = os.path.dirname(argv)
    sys.path.append(os.path.join(ts_path, '..', '..'))
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
                if re.match(r'test_.*\.py$', filename):
                    file = os.path.join(root, filename).rsplit('.', 1)[0]\
                        .replace(file_path + "/", "").replace("/", ".")
                    ts_list.append(file)

    ts_count = test_count = pass_count = fail_count = 0
    ts_start_time = time.time()
    for ts in ts_list:
        print('\n####### Test Suite: %s ######' %ts)
        ts_count += 1
        try:
            ts_module = __import__('sspl.sspl_test.%s' %ts, fromlist=[ts])
            # Initialization
            init = getattr(ts_module, 'init')
            init(args)
        except Exception as e:
            print('FAILED: Error: %s #@#@#@' %e)
            fail_count += 1
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

            except (TestFailed, Exception) as e:
                print('%s:%s: FAILED #@#@#@' %(ts, test.__name__))
                print('    %s\n' %e)
                fail_count += 1

    duration = time.time() - ts_start_time
    print('\n***************************************')
    print('TestSuite:%d Tests:%d Passed:%d Failed:%d TimeTaken:%ds' \
        %(ts_count, test_count, pass_count, fail_count, duration))
    print('***************************************')

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
        stop_rabbitMQ_msg_processors()
    except Exception as e:
        print(e, traceback.format_exc())
        stop_rabbitMQ_msg_processors()
