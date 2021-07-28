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
        channel = self.ssh.invoke_shell()

    def execute_remote_cmd(self, cmd):
        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        while not stdout.channel.exit_status_ready():
            time.sleep(1)
            if stdout.channel.recv_ready():
                r1, w1, x1 = select.select([stdout.channel], [], [], 0.0)
                if len(r1) > 0:
                    print(stdout.channel.recv(1024).decode('utf-8'))


class TestReceiverRunner:
    def __init__(self, ts, tc, mode):
        self.ts = ts
        self.tc = tc
        self.mode = mode

    def run_tests(self):
        ts_module = __import__(self.ts, fromlist=[self.ts])
        try:
            init = getattr(ts_module, 'init')
            init(args)
            duration = 0
            start_time = time.time()
            test_case = getattr(ts_module, self.tc)
            test_case(self.mode)
            duration += time.time() - start_time
            print('%s:%s: PASSED (Time: %ds)' % (self.ts, self.tc, duration))
        except (TestFailed, Exception) as e:
            print(traceback.format_exc())
            print('%s:%s: FAILED #@#@#@' % (self.ts, self.tc))

    @staticmethod
    def initialize_test_processes():
        init_messaging_msg_processors('IngressProcessorTests')
        print('Receiver initialized')


if __name__ == '__main__':
    try:
        arg_parser = argparse.ArgumentParser(
            usage="%(prog)s [-h] [--mode] [--ts] [--tc]",
            formatter_class=argparse.RawDescriptionHelpFormatter)
        arg_parser.add_argument("--mode", choices=["sender", "receiver"])
        arg_parser.add_argument("--ts", required=True)
        arg_parser.add_argument("--tc", required=True)
        args = arg_parser.parse_args()
        test_receiver_runner = TestReceiverRunner(args.ts, args.tc, args.mode)
        test_receiver_runner.initialize_test_processes()
        test_receiver_runner.run_test()
    except Exception as e:
        print(e, traceback.format_exc())
        stop_messaging_msg_processors()
