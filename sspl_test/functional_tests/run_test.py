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
import time
import traceback
import argparse

from pathlib import Path
import paramiko

from framework.messaging.egress import TestEgressProcessor
from generate_test_report import generate_html_report
from common import TestFailed

from framework.utils.conf_utils import Conf, SSPL_TEST_CONF

skip_group_prefixes = {
    "REALSTORSENSORS": "alerts.realstor",
    "NODEHWSENSOR": "alerts.node",
    "SYSTEMDWATCHDOG": None,
    "RAIDSENSOR": None,
}


def conf_skipped_prefixes():
    for group in skip_group_prefixes.keys():
        monitor = Conf.get(SSPL_TEST_CONF, f"{group}>monitor", "true")
        if monitor not in ["true", True]:
            yield skip_group_prefixes[group]


result = {}


class MessageHandler:
    def __init__(self):
        self.process_hander = TestEgressProcessor()

    def send(self, request):
        self.process_hander.publish(request)


class SSHHandler:
    def __init__(self, host, username, password):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(host, username=username, password=password, port=22)
        self.stdin = None
        self.stdout = None
        self.stderr = None
        self.outputs = []
        self.completed = None
        self.remote_roller = None

    def execute_remote_test(self, ts, tc):
        cmd = (
            "python3 /opt/seagate/cortx/sspl/sspl_test/functional_tests/sspl_test_receiver.py --ts %s --tc %s"
            % (ts, tc)
        )
        print(cmd)
        self.completed = False
        self.stdin, self.stdout, self.stderr = self.ssh.exec_command(cmd)
        self.remote_roller = self.check_remote_output()
        while True:
            for output in self.remote_roller:
                print("waiting for test case listen confirmation", output)
                if "waiting for %s:%s" % (ts, tc) in output:
                    print("Received test case listen confirmation")
                    return True
                else:
                    time.sleep(0.1)
            time.sleep(0.1)

    def check_remote_output(self):
        while True:
            time.sleep(0.1)
            if self.stdout.channel.recv_ready():
                r1, w1, x1 = select.select([self.stdout.channel], [], [], 0.0)
                if len(r1) > 0:
                    output = self.stdout.channel.recv(4096).decode("utf-8")
                    self.outputs.append(output)
                    yield output
            elif self.stdout.channel.exit_status_ready():
                break
        output = self.stdout.channel.recv(4096).decode("utf-8")
        self.outputs.append(output)
        yield output
        self.completed = True


class TestSenderRunner:
    def __init__(self, plan, type, mode, config):
        self.plan = plan
        self.type = type
        self.mode = mode
        self.config = config
        self.peers = {}
        self.message_handler = MessageHandler()
        if not self.config:
            self.peers["localhost"] = SSHHandler("localhost", "root", "")

    def connect_to_peers(self):
        with open(self.config) as cf:
            try:
                cjson = json.loads(cf.read())
                for node_config in cjson["nodes"]:
                    ssh_handler = SSHHandler(
                        node_config["host"],
                        node_config["username"],
                        node_config["password"],
                    )
                    self.peers[node_config["host"]] = ssh_handler
            except IOError:
                print("Error in config file loading")
                print(traceback.format_exc())

    def very_if_test_is_remotely_passed(self, ts, tc):
        while True:
            all_completed = True
            for peer, ssh_handler in self.peers.items():
                if ssh_handler.completed:
                    for line in ssh_handler.outputs:
                        if "%s:%s: PASSED" % (ts, tc) in line:
                            return True
                else:
                    all_completed = False
                    for output in ssh_handler.remote_roller:
                        print(output)
                        if "%s:%s: PASSED" % (ts, tc) in output:
                            return True
            if all_completed:
                return False

    def call_receivers(self, test_module, test_case):
        for peer, ssh_handler in self.peers.items():
            ssh_handler.execute_remote_test(test_module, test_case)

    def run_tests(self, mode):
        with open(Path(__file__).parent / "plans" / (self.plan + ".pln")) as f:
            ts_list = [x.strip() for x in f.readlines()]
        ts_count = test_count = pass_count = fail_count = skip_count = 0
        ts_start_time = time.time()

        for ts in ts_list:
            print("\n####### Test Suite: %s ######" % ts)
            ts_count += 1
            ts_module = __import__(ts, fromlist=[ts])

            found_failed_test = False
            duration = 0
            for test_class in ts_module.test_list:
                test_count += 1
                try:
                    start_time = time.time()
                    self.call_receivers(ts, test_class.__name__)
                    test_class_obj = test_class()
                    test_class_obj.init()
                    request = test_class_obj.request()
                    self.message_handler.send(request)
                    test_passed = self.very_if_test_is_remotely_passed(
                        ts, test_class.__name__
                    )
                    duration += time.time() - start_time
                    if test_passed:
                        print(
                            "%s:%s: PASSED (Time: %ds)"
                            % (ts, test_class.__name__, duration)
                        )
                        pass_count += 1
                    else:
                        raise Exception(
                            "All remotes are closed. Unable to verify the test case"
                        )
                except (TestFailed, Exception):
                    print(traceback.format_exc())
                    print("%s:%s: FAILED #@#@#@" % (ts, test_class.__name__))
                    fail_count += 1
                    found_failed_test = True
            if not found_failed_test:
                result.update({ts: {"Pass": duration}})
            else:
                result.update({ts: {"Fail": duration}})

        # View of consolidated test suite status
        print("\n", "*" * 90)
        print("{:60} {:10} {:10}".format("TestSuite", "Status", "Duration(secs)"))
        print("*" * 90)
        for k, v in result.items():
            print(
                "{:60} {:10} {:10}s".format(
                    k, list(v.keys())[0], int(list(v.values())[0])
                )
            )

        duration = time.time() - ts_start_time
        print("\n****************************************************")
        print(
            "TestSuite:%d Tests:%d Passed:%d Failed:%d Skipped:%d TimeTaken:%ds"
            % (ts_count, test_count, pass_count, fail_count, skip_count, duration)
        )
        print("******************************************************")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        usage="%(prog)s [-h] [-t]", formatter_class=argparse.RawDescriptionHelpFormatter
    )
    arg_parser.add_argument("--mode", choices=["sender", "receiver"])
    arg_parser.add_argument("--type", choices=["vm", "hw"])
    arg_parser.add_argument("--plan", required=True)
    args = arg_parser.parse_args()
    test_runner = TestSenderRunner(args.plan, args.type, args.mode, None)
    test_runner.run_tests(args.mode)
    generate_html_report(result)
