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
try:
    import salt.client
    from sspl_constants import component, file_store_config_path, salt_provisioner_pillar_sls, SSPL_STORE_TYPE, StoreTypes
except Exception as e:
    from framework.base.sspl_constants import component, salt_provisioner_pillar_sls, file_store_config_path, SSPL_STORE_TYPE, StoreTypes
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
        if is_init:
            self.read_dev_conf()
        elif is_test:
            self.read_test_conf(test_config_path)
        else:
            self.read_salt_conf()

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

    def read_salt_conf(self):
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
                value = self.store.get(component + '/' + section + '/' + key)
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
                pairs = self.store.get(component + '/' + section + '/' , recurse=True)
            else:
                raise Exception("{} Invalid store type object.".format(self.store))
        except (RuntimeError, Exception) as e:
            # Taking values from normal configparser in dev env
            pairs = self.store.items(section)

        for item in pairs:
            value_list.append(item[1])
        return value_list
