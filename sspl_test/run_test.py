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
import json
import select
import sys, os, time
import traceback
import re
import argparse

from pathlib import Path
import paramiko

from generate_test_report import generate_html_report
from common import (TestFailed, init_messaging_msg_processors,
                    stop_messaging_msg_processors)
from framework.utils.conf_utils import Conf, SSPL_TEST_CONF

skip_group_prefixes = {
    "REALSTORSENSORS": "alerts.realstor",
    "NODEHWSENSOR": "alerts.node",
    "SYSTEMDWATCHDOG": None,
    "RAIDSENSOR": None,
}


def conf_skipped_prefixes():
    for group in skip_group_prefixes.keys():
        monitor = Conf.get(SSPL_TEST_CONF, f"{group}>monitor", 'true')
        if monitor not in ['true', True]:
            yield skip_group_prefixes[group]


result = {}


class SSHHandler:
    def __init__(self, host, username, password):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(host, username=username, password=password, port=22)
        self.stdin = None
        self.stdout = None
        self.stderr = None

    def execute_remote_test(self, ts, tc):
        cmd = 'sudo /opt/seagate/cotrx/sspl/sspl_test/sspl_test_receiver.py --ts %s --tc %s --mode receiver' % (
            ts, tc) 
        print(cmd)
        self.stdin, self.stdout, self.stderr = self.ssh.exec_command(cmd)
        for output in self.check_remote_output():
            if '%s.%s listening' % (ts, tc) in output:
                return True

    def check_remote_output(self):
        while not self.stdout.channel.exit_status_ready():
            time.sleep(1)
            if self.stdout.channel.recv_ready():
                r1, w1, x1 = select.select([self.stdout.channel], [], [], 0.0)
                if len(r1) > 0:
                    yield self.stdout.channel.recv(1024).decode('utf-8')


class TestSenderRunner:
    def __init__(self, plan, type, mode, config):
        self.plan = plan
        self.type = type
        self.mode = mode
        self.config = config
        self.peers = {}
        if not self.config:
            self.peers['localhost'] = SSHHandler('localhost', 'root', 'seagate')

    def connect_to_peers(self):
        with open(self.config) as cf:
            try:
                cjson = json.loads(cf.read())
                for node_config in cjson["nodes"]:
                    ssh_handler = SSHHandler(node_config['host'], node_config['username'], node_config['password'])
                    self.peers[node_config['host']] = ssh_handler
            except IOError:
                print('Error in config file loading')
                print(traceback.format_exc())

    def very_if_test_is_remotely_passed(self, ts, tc):
        for peer, ssh_handler in self.peers.items():
            for output in ssh_handler.check_remote_output():
                if '%s.%s passed' % (ts, tc) in output:
                    return True

    def call_receivers(self, test_module, test_case):
        for peer, ssh_handler in self.peers.items():
            started = ssh_handler.execute_remote_test(test_module, test_case)
            if started:
                continue

    def run_tests(self, mode):
        with open(Path(__file__).parent / 'plans' / (self.plan + '.pln')) as f:
            ts_list = [x.strip() for x in f.readlines()]
        ts_count = test_count = pass_count = fail_count = skip_count = 0
        ts_start_time = time.time()

        skipped_prefixes = list(conf_skipped_prefixes())
        for ts in ts_list:
            print('\n####### Test Suite: %s ######' % ts)
            ts_count += 1
            if any((ts.startswith(p) for p in skipped_prefixes if p is not None)):
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
                print('FAILED: Error: %s #@#@#@' % e)
                fail_count += 1
                result.update({ts: {"Fail": 0}})
                continue

            # Actual test execution
            found_failed_test = False
            duration = 0
            for test_module in ts_module.test_list:
                test_count += 1
                try:
                    start_time = time.time()
                    self.call_receivers(ts, test_module.__name__)
                    test_module(mode)
                    duration += time.time() - start_time
                    self.very_if_test_is_remotely_passed(ts, test_module)
                    print('%s:%s: PASSED (Time: %ds)' % (ts, test_module.__name__, duration))
                    pass_count += 1
                except (TestFailed, Exception) as e:
                    print(traceback.format_exc())
                    print('%s:%s: FAILED #@#@#@' % (ts, test_module.__name__))
                    fail_count += 1
                    found_failed_test = True
            if not found_failed_test:
                result.update({ts: {"Pass": duration}})
            else:
                result.update({ts: {"Fail": duration}})

        # View of consolidated test suite status
        print('\n', '*' * 90)
        print('{:60} {:10} {:10}'.format("TestSuite", "Status", "Duration(secs)"))
        print('*' * 90)
        for k, v in result.items():
            print('{:60} {:10} {:10}s'.format(k, list(v.keys())[0], int(list(v.values())[0])))

        duration = time.time() - ts_start_time
        print('\n****************************************************')
        print('TestSuite:%d Tests:%d Passed:%d Failed:%d Skipped:%d TimeTaken:%ds' \
              % (ts_count, test_count, pass_count, fail_count, skip_count, duration))
        print('******************************************************')

    @staticmethod
    def initialize_test_processes():
        init_messaging_msg_processors('EgressProcessorTests')


if __name__ == '__main__':
    try:
        arg_parser = argparse.ArgumentParser(
            usage="%(prog)s [-h] [-t]",
            formatter_class=argparse.RawDescriptionHelpFormatter)
        arg_parser.add_argument("--mode", choices=["sender", "receiver"])
        arg_parser.add_argument("--type", choices=["vm", "hw"])
        arg_parser.add_argument("--plan", required=True)
        args = arg_parser.parse_args()
        test_runner = TestSenderRunner(args.plan, args.type, args.mode, None)
        test_runner.initialize_test_processes()
        test_runner.run_tests(args.mode)
        generate_html_report(result)
        stop_messaging_msg_processors()
    except Exception as e:
        print(e, traceback.format_exc())
        stop_messaging_msg_processors()
