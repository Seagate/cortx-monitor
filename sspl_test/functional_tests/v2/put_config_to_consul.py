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

import os
import sys
import consul
from configparser import ConfigParser

CONSUL_HOST = "127.0.0.1"
CONSUL_PORT = "8500"


class TestConfig(object):
    @staticmethod
    def set_config():
        try:
            host = os.getenv("CONSUL_HOST", CONSUL_HOST)
            port = os.getenv("CONSUL_PORT", CONSUL_PORT)
            consul_conn = consul.Consul(host=host, port=port)

            # for test configs
            print("reading test conf file and inserting data to consul.")
            test_component = "sspl_test/config"
            path_to_conf_file = "/opt/seagate/cortx/sspl/sspl_test/conf/sspl_tests.conf"
            if os.path.exists(path_to_conf_file):
                print("Using conf file : {}".format(path_to_conf_file))
            else:
                conf_directory = os.path.dirname(os.path.abspath(__file__))
                path_to_conf_file = os.path.join(conf_directory, "sspl_tests.conf")
                print("Using conf file : {}".format(path_to_conf_file))

            parser = ConfigParser()
            parser.read(path_to_conf_file)
            for sect in parser.sections():
                for k, v in parser.items(sect):
                    consul_conn.kv.put(test_component + "/" + sect + "/" + k, v)

        except Exception as serror:
            print("Error occured: {}".format(serror))
            print("Exiting ...")
            sys.exit(os.EX_USAGE)


TestConfig.set_config()
