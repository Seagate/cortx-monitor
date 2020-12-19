# Copyright (c) 2001-2020 Seagate Technology LLC and/or its Affiliates
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
  Description:       Configuration file reader
 ****************************************************************************
"""

import os
import sys
import consul
import configparser
import time
import requests
try:
    import salt.client
except ModuleNotFoundError:
    pass
from framework.base.sspl_constants import (component, salt_provisioner_pillar_sls, file_store_config_path,
        SSPL_STORE_TYPE, StoreTypes, salt_uniq_passwd_per_node, COMMON_CONFIGS, SSPL_CONFIGS, CONSUL_PORT,
        MAX_CONSUL_RETRY, WAIT_BEFORE_RETRY, CONSUL_ERR_STRING, CONSUL_HOST)
from framework.utils.consulstore import ConsulStore
from framework.utils.filestore import FileStore


class ConfigReader(object):
    """Configuration reader for notification sender"""

    # Available exceptions from ConfigParser
    MissingSectionHeaderError   = configparser.MissingSectionHeaderError
    NoSectionError              = configparser.NoSectionError
    NoOptionError               = configparser.NoOptionError
    Error                       = configparser.Error

    def __init__(self, is_init=False, is_test=False, test_config_path=None):
        """Constructor for ConfigReader
        @param config: configuration file name
        """
        self.store = None
        self.consul_conn = None
        self.is_init = is_init
        if is_init:
            if PRODUCT_NAME == "LDR_R1":
                self.read_dev_conf()
            host = os.getenv('CONSUL_HOST', CONSUL_HOST)
            port = os.getenv('CONSUL_PORT', CONSUL_PORT)
            for retry_index in range(0, MAX_CONSUL_RETRY):
                try:
                    self.consul_conn = consul.Consul(host=host, port=port)
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
                        print(f'Error[{gerr}] consul error')
                        break
        elif is_test:
            self.read_test_conf(test_config_path)
        else:
            self.read_prod_conf()

    def read_dev_conf(self):
        """
        Old way of reading config, Only replacing the file with salt API
        """
        print("ENV=dev")
        try:
            store_type = os.getenv('SSPL_STORE_TYPE', SSPL_STORE_TYPE)
            # We can't import Consulestore and Filestore in the sspl_init hence using this alternative
            # For consulstore we using salt and for filestore we using configparser with /etc/sspl.conf
            if store_type == StoreTypes.CONSUL.value:
                print("Doing init and taking key values from salt provisioning node configuration")
                new_conf = salt.client.Caller().function('pillar.get', salt_provisioner_pillar_sls)
                str_keys = [k for k,v in new_conf.items() if isinstance(v, str)]
                for k in str_keys:
                    del new_conf[k]
                common_cluster_id = salt.client.Caller().function('grains.get', 'cluster_id')
                # Password is same for RABBITMQINGRESSPROCESSOR, RABBITMQEGRESSPROCESSOR & LOGGINGPROCESSOR
                rbmq_pass = salt.client.Caller().function('pillar.get',
                            'rabbitmq:sspl:RABBITMQINGRESSPROCESSOR:password')
                if common_cluster_id:
                    new_conf.get('SYSTEM_INFORMATION')['cluster_id'] = common_cluster_id
                for sect in salt_uniq_passwd_per_node:
                    if rbmq_pass:
                        new_conf.get(sect)['password'] = rbmq_pass
                self.store = configparser.ConfigParser(allow_no_value=True)
                self.store.read_dict(new_conf)
            elif store_type == StoreTypes.FILE.value:
                print("Checking and reading file from local config path => /etc/sspl.conf")
                self.store = configparser.ConfigParser(allow_no_value=True)
                self.store.read(file_store_config_path)
            else:
                print("Exiting... Invalid store type")
                sys.exit(os.EX_USAGE)
        except salt.exceptions.SaltClientError as serror:
            print("Error in connecting salt client: {}".format(serror))
            print("Checking and reading file from local config path => /etc/sspl.conf")
            config = file_store_config_path
            if not os.path.isfile(config):
                raise IOError("config file %s does not exist." %
                            config)
            elif not os.access(config, os.R_OK):
                raise IOError("config file %s is not readable. "
                            "Please check permission." %
                            config)
            else:
                self.store = configparser.RawConfigParser()
                self.store.read(config)

    def read_test_conf(self, test_config_path):
        print("ENV=test")
        config = test_config_path
        if not os.path.isfile(config):
            raise IOError("config file %s does not exist." %
                        config)
        elif not os.access(config, os.R_OK):
            raise IOError("config file %s is not readable. "
                        "Please check permission." %
                        config)
        else:
            self.store = configparser.RawConfigParser()
            self.store.read(config)

    def read_prod_conf(self):
        """
        Specific function for executable binary.
        """
        print("ENV=prod")
        print("Running via sspl service and taking key values from store factory")
        from framework.utils.store_factory import store
        self.store = store

    def _get_value(self, section, key):
        """Get a single value by section and key

        @param section: section name
        @param key: key name
        @raise ConfigParser.NoSectionError: when the specified section does
            not exist
        @raise ConfigParser.NoOptionError: when the specified key does not

            exist
        """
        value = None
        try:
            if self.store is not None and isinstance(self.store, FileStore):
                value = self.store.get(section, key)
            elif self.store is not None and isinstance(self.store, ConsulStore):
                if section not in COMMON_CONFIGS:
                    value = self.store.get(component + '/' + section + '/' + key)
                elif key in SSPL_CONFIGS or section.lower() in SSPL_CONFIGS:
                    value = self.store.get(component + '/' + section + '/' + key)
                else:
                    value = self.get_from_common_config(section, key)
            elif self.store is None and self.consul_conn:
                if section not in COMMON_CONFIGS:
                    value = self.consul_conn.kv.get(component + '/' + section + '/' + key)[1]
                else:
                    value = self.consul_conn.kv.get(section.lower() + '/' + key)[1]
                if value and value["Value"]:
                    value = value["Value"]
            else:
                raise Exception("{} Invalid store type object.".format(self.store))
        except (RuntimeError, Exception) as e:
            # Taking values from normal configparser in dev env
            if section in COMMON_CONFIGS:
                value = self.get_from_common_config(section, key)
            else:
                value = self.store.get(section, key)

        if value in [None, '', ['']]:
            return ''
        elif isinstance(value, str):
            return value.strip()
        else:
            return value.decode('utf-8').strip()

    def _get_value_list(self, section, key):
        """Get a list of values given the section name and key

        @param section: section name
        @param key: key name
        @raise ConfigParser.NoSectionError: when the specified section does
            not exist
        @raise ConfigParser.NoOptionError: when the specified key does not
            exist
        """
        values_from_config_parser = self._get_value(section, key)
        if values_from_config_parser == '':
            return []
        else:
            split_vals = values_from_config_parser.split(',')
            stripped_vals = [val.strip() for val in split_vals]
            return stripped_vals

    def _get_value_with_default(self, section, key, default_value):
        """helper function to read value with default function
        in case there is exception or incomplete configuration file
        we do provide default value for certain settings
        """
        try:
            val = self._get_value(section, key)
            if val == '':
                return default_value
            return val
        except Exception as ex:
            print(f'Error reading config value: {ex}. Returning default value')
            return default_value

    def _get_all_values_for_section(self, section):
        """Get all values for all the keys in the section"""
        value_list = list()
        try:
            if self.store is not None and isinstance(self.store, FileStore):
                pairs = self.store.items(section)
            elif self.store is not None and isinstance(self.store, ConsulStore):
                if section not in COMMON_CONFIGS:
                    pairs = self.store.get(component + '/' + section + '/' , recurse=True)
                else:
                    pairs = self.get_from_common_config(section)
            else:
                raise Exception("{} Invalid store type object.".format(self.store))
        except (RuntimeError, Exception) as e:
            # Taking values from normal configparser in dev env
            if section in COMMON_CONFIGS:
                pairs = self.get_from_common_config(section)
            else:
                pairs = self.store.items(section)

        for item in pairs:
            value_list.append(item[1])
        return value_list

    def get_from_common_config(self, section, key=None):
        if self.is_init:
            if self.consul_conn is not None and section in COMMON_CONFIGS:
                if key is None:
                    val = self.kv_get(section.lower() + '/', recurse=True)
                else:
                    if section.lower() == 'rabbitmqcluster':
                        val = self.kv_get(key)
                    else:
                        val = self.kv_get(section.lower() + '/' + key)
            elif self.store is not None and isinstance(self.store, configparser.RawConfigParser):
                val = self.store.get(section, key)
        else:
            if key is None:
                val = self.store.get(section.lower() + '/', recurse=True)
            else:
                if section.lower() == 'rabbitmqcluster':
                    val = self.store.get(key)
                else:
                    val = self.store.get(section.lower() + '/' + key)
        return val

    def _get_key(self, key):
        """remove '/' from begining of the key"""
        if key[:1] ==  "/":
            return key[1:]
        else:
            return key

    def kv_get(self, key, **kwargs):
        for retry_index in range(0, MAX_CONSUL_RETRY):
            try:
                _opt_recurse = kwargs.get("recurse", False)
                key = self._get_key(key)
                data = self.consul_conn.kv.get(key, recurse=_opt_recurse)[1]
                if data:
                    data = data["Value"]
                    try:
                        data = pickle.loads(data)
                    except:
                        pass
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
                    print(f'Error[{gerr}] consul error')
                    break
        return data
