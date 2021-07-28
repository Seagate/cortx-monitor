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


import time
import traceback
import argparse 

from common import TestFailed
from messaging.ingress_processor_tests import IngressProcessorTests


class TestReceiverRunner:
    def __init__(self, ts, tc, mode):
        self.ts = ts
        self.tc = tc
        self.mode = mode
        self.message_reader = IngressProcessorTests()

    def run_test(self):
        ts_module = __import__(self.ts, fromlist=[self.ts])
        duration = 0
        start_time = time.time()
        test_class = getattr(ts_module, self.tc)
        test_obj = test_class()
        print('waiting for %s:%s' % (self.ts, self.tc), flush=True)
        for msg in self.message_reader.message_reader():
            valid_msg = test_obj.filter(msg)
            if valid_msg:
                try:
                    test_obj.response(msg)
                    duration += time.time() - start_time
                    print('%s:%s: PASSED (Time: %ds)' % (self.ts, self.tc, duration), flush=True)
                except (TestFailed, Exception):
                    print(traceback.format_exc(), flush=True)
                    print('%s:%s: FAILED #@#@#@' % (self.ts, self.tc), flush=True)
                break


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(
        usage="%(prog)s [-h] [--mode] [--ts] [--tc]",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    arg_parser.add_argument("--mode", choices=["sender", "receiver"])
    arg_parser.add_argument("--ts", required=True)
    arg_parser.add_argument("--tc", required=True)
    args = arg_parser.parse_args()
    test_receiver_runner = TestReceiverRunner(args.ts, args.tc, args.mode)
    test_receiver_runner.run_test()
