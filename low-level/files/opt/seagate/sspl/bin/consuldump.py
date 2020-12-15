#!/usr/bin/python3.6

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
import datetime
import consul
import pickle
import json
import argparse
import time
import requests
import sys
# Add the top level directories
sys.path.insert(0, f'/opt/seagate/cortx/sspl/low-level')
from framework.base.sspl_constants import MAX_CONSUL_RETRY, WAIT_BEFORE_RETRY, CONSUL_HOST, CONSUL_PORT, CONSUL_ERR_STRING

class ConsulDump():

    def __init__(self, localtion=os.getcwd(), dir_prefix="", existing=False, name=None, keys={}):
        self.time = str(int(time.time()))
        self.dir_prefix = dir_prefix
        self.location = localtion
        self.file_name = name
        self.keys = keys
        self.existing = existing
        for retry_index in range(0, MAX_CONSUL_RETRY):
            try:
                self.consul = consul.Consul(host=CONSUL_HOST, port=CONSUL_PORT)
                break
            except requests.exceptions.ConnectionError as connerr:
                print(f'Error[{connerr}] consul connection refused Retry Index {retry_index}')
                time.sleep(WAIT_BEFORE_RETRY)
            except Exception as gerr:
                # TODO: optimize the if-else here and wherever this similar code is used
                consulerr = str(gerr)
                if CONSUL_ERR_STRING == consulerr:
                    print(f'Error[{gerr}] consul connection refused Retry Index {retry_index}')
                    time.sleep(WAIT_BEFORE_RETRY)
                else:
                    print(f'Error[{gerr}] consul error')
                    break

    def get_dir(self):
        if not self.existing:
            if self.file_name:
                return f"{self.location}/{self.file_name}"
            elif "/" in self.dir_prefix:
                raise TypeError("/ is not accepted as dir_prefix")
            elif self.dir_prefix:
                return f"{self.location}/consuldump_{self.dir_prefix}_{self.time}"
            else:
                return f"{self.location}/consuldump_{self.time}"
        else:
            return self.location

    def mkdir(self, path):
        os.makedirs(path, exist_ok=True)

    def get_values(self, key):
        value = []
        for retry_index in range(0, MAX_CONSUL_RETRY):
            try:
                value = self.consul.kv.get(key, recurse=True)[1]
                if not value:
                    value = []
                break
            except requests.exceptions.ConnectionError as connerr:
                print(f'Error[{connerr}] consul connection refused Retry Index {retry_index}')
                time.sleep(WAIT_BEFORE_RETRY)
            except Exception as gerr:
                consulerr = str(gerr)
                if CONSUL_ERR_STRING == consulerr:
                    print(f'Error[{gerr}] consul connection refused Retry Index {retry_index}')
                    time.sleep(WAIT_BEFORE_RETRY)
                else:
                    print(f'Error{gerr} while reading data from consul {key}')
                    break
        return value

    def get_pretty_file_content(self, data):
        deserialized = ""
        try:
            deserialized = pickle.loads(data)
            return json.dumps(deserialized, indent=4)
        except pickle.UnpicklingError:
            return data.decode()
        except TypeError:
            return deserialized.__str__()

    def dump(self):
        for key, options in self.keys.items():
            if not options["hierarchy"]:
                if options["dir"]:
                    path = f'{self.get_dir()}/{options["dir"]}'
                else:
                    path = f'{self.get_dir()}/{key.replace("/", "_")}'
                for value in self.get_values(key):
                    self.mkdir(os.path.dirname(path))
                    with open(path, 'a') as outfile:
                        outfile.write(f"{value['Key']}:\n")
                        outfile.write(f"{self.get_pretty_file_content(value['Value'])}\n")
            else:
                for value in self.get_values(key):
                    path = f"{self.get_dir()}/{options['dir']}/{value['Key']}"
                    self.mkdir(os.path.dirname(path))
                    with open(path, 'w') as outfile:
                        outfile.write(self.get_pretty_file_content(value['Value']))

if __name__ == "__main__":
    example = """
examples:
  consuldump.py var/

  Dump keys having prefix var/ in consuldump-{timestamp}

  consuldump.py -l /home/root/  var/

  Dump data at different location

  consuldump.py -p before_removing_disk var/

  Add prefix in target directory
  consuldump_before_removing_disk-{timestamp}

  consuldump.py -d sspl-config  sspl/config

  Dump all keys having prefix sspl/config in sspl-config file

  consuldump.py -d encl/data --hierarchy var/

  Create directory tree at encl/data(inside location/consuldump-{timestamp})

  consuldump.py --existing var/

  Use existing directory instead of creating new(consuldump_{timestamp})

  consuldump.py -n dump_sample var/

  generate consuldump folder with the name of dump_sample
"""
    my_parser = argparse.ArgumentParser(description="Dump consul data", epilog=example, formatter_class=argparse.RawDescriptionHelpFormatter)
    my_parser.add_argument('-l', '--location', action='store',default=os.getcwd(), help='dump data at given location')
    my_parser.add_argument('-p','--prefix', action='store', default='',
                           help='add prefix in dump directory, usefull when you need to differentiate between two \
                                 dumps.')
    my_parser.add_argument('-n', '--name', action='store', default='', help="rename dump file with given name")
    my_parser.add_argument('--existing', action='store_true', help="use existing directory, instead of creating new with consuldump_{timestamp}")
    my_parser.add_argument('--hierarchy', action='store_true', help="create directory tree, if key is having '/'")
    my_parser.add_argument('-d', '--dir', action='store',default='', help='create dump for a key in dir, if passed along with --hierarchy. if --hierarchy is not passed, all matching keys data will be dumped in this file')
    my_parser.add_argument('key', action='store')


    args = my_parser.parse_args()

    # When using programmatically many keys can be passed
    # limiting to only one key in cli mode as it requires different optional args per positional arg
    # need hierarchy and dir for every key
    keys = {args.key: {"hierarchy": args.hierarchy, "dir":args.dir}}
    ConsulDump(localtion=args.location, dir_prefix=args.prefix, keys=keys,
                existing=args.existing, name=args.name).dump()
