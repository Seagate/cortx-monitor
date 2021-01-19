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
import configparser
from cortx.utils.conf_store import ConfStore
from sspl_test.framework.base.sspl_constants import component, file_store_config_path, SSPL_STORE_TYPE, StoreTypes, CONSUL_HOST, CONSUL_PORT
from sspl_test.framework.utils.service_logging import logger

# Onward LDR_R2, consul will be abstracted out and won't exist as hard dependency for SSPL
if SSPL_STORE_TYPE == 'consul':
    import consul

class ConfigReader(object):
    """Configuration reader for notification sender"""

    # Available exceptions from ConfigParser
    MissingSectionHeaderError   = configparser.MissingSectionHeaderError
    NoSectionError              = configparser.NoSectionError
    NoOptionError               = configparser.NoOptionError
    Error                       = configparser.Error

    def __init__(self):
        """Constructor for ConfigReader
        @param config: configuration file name
        """
        self.store = None
        self.load_conf = False
        try:
            store_type = os.getenv('SSPL_STORE_TYPE', SSPL_STORE_TYPE)
            if store_type == StoreTypes.FILE.value:
                self.store = configparser.RawConfigParser()
                self.store.read([file_store_config_path])
            elif store_type == StoreTypes.CONSUL.value:
                host = os.getenv('CONSUL_HOST', CONSUL_HOST)
                port = os.getenv('CONSUL_PORT', CONSUL_PORT)
                self.store = consul.Consul(host=host, port=port)
            elif store_type == StoreTypes.CONF.value:
                self.store = ConfStore()
            else:
                raise Exception("{} type store is not supported".format(store_type))

        except Exception as serror:
            print("Error in connecting either with file or consul store: {}".format(serror))
            print("Exiting ...")
            sys.exit(os.EX_USAGE)

    def load_conf_store(self):
        if not self.load_conf:
            Conf.load('test_config', f'yaml://{file_store_config_path}')
            self.load_conf = True

    def get_value(self, section, key):
        '''public method to get_value'''
        return self._get_value(section, key)

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
            if self.store is not None and isinstance(self.store, configparser.RawConfigParser):
                value = self.store.get(section, key)
            elif self.store is not None and isinstance(self.store, consul.Consul):
                value = self.kv_get(component + '/' + section + '/' + key)
            elif self.store is not None and isinstance(self.store, Conf):
                if not self.load_conf:
                    self.load_conf_store()
                value = self.store.get('test_config', f'{section}>{key}')
            else:
                raise Exception("{} Invalid store type object.".format(self.store))
        except (RuntimeError, Exception) as e:
            # Taking values from normal configparser in dev env
            value = self.store.get(section, key)

        if value in [None, '', ['']]:
            return ''
        elif isinstance(value, str):
            return value.strip()
        else:
            return value.decode('utf-8').strip()

    def get_value_list(self, section, key):
        '''public method to _get_value_list'''
        return self._get_value_list(section, key)

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
        if isinstance(values_from_config_parser, list):
            return values_from_config_parser
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
            if self.store is not None and isinstance(self.store, configparser.RawConfigParser):
                pairs = self.store.items(section)
            elif self.store is not None and isinstance(self.store, consul.Consul):
                pairs = self.kv_get(component + '/' + section + '/', recurse=True)
            else:
                raise Exception("{} Invalid store type object.".format(self.store))
        except (RuntimeError, Exception) as e:
            # Taking values from normal configparser in dev env
            pairs = self.store.items(section)

        for item in pairs:
            value_list.append(item[1])
        return value_list

    def _get_key(self, key):
        """remove '/' from begining of the key"""

        if key[:1] ==  "/":
            return key[1:]
        else:
            return key

    def kv_get(self, key, **kwargs):
        try:
            _opt_recurse = kwargs.get("recurse", False)
            key = self._get_key(key)
            data = self.store.kv.get(key, recurse=_opt_recurse)[1]
            if data:
                data = data["Value"]
                try:
                    data = pickle.loads(data)
                except:
                    pass
        except Exception as gerr:
            logger.warn("Error{0} while reading data from consul {1}"\
                .format(gerr, key))

        return data
