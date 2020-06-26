"""
 ****************************************************************************
 Filename:          config_reader.py
 Description:       Configuration file reader
 Creation Date:     01/14/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import os
import sys
import consul
import configparser
from framework.base.sspl_constants import component, file_store_config_path, SSPL_STORE_TYPE, StoreTypes, CONSUL_HOST, CONSUL_PORT


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
        try:
            store_type = os.getenv('SSPL_STORE_TYPE', SSPL_STORE_TYPE)
            if store_type == StoreTypes.FILE.value:
                self.store = configparser.RawConfigParser()
                self.store.read(file_store_config_path)
            elif store_type == StoreTypes.CONSUL.value:
                host = os.getenv('CONSUL_HOST', CONSUL_HOST)
                port = os.getenv('CONSUL_PORT', CONSUL_PORT)
                self.store = consul.Consul(host=host, port=port)
            else:
                raise Exception("{} type store is not supported".format(store_type))

        except Exception as serror:
            print("Error in connecting either with file or consul store: {}".format(serror))
            print("Exiting ...")
            sys.exit(os.EX_USAGE)

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
