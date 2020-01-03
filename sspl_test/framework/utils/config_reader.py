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
import configparser

from sspl_test.framework.utils.service_logging import logger


class ConfigReader(object):
    """Configuration reader for notification sender"""

    # Available exceptions from ConfigParser
    MissingSectionHeaderError   = configparser.MissingSectionHeaderError
    NoSectionError              = configparser.NoSectionError
    NoOptionError               = configparser.NoOptionError
    Error                       = configparser.Error

    def __init__(self, config):
        """Constructor for ConfigReader

        @param config: configuration file name
        """
        self._config_parser = configparser.RawConfigParser()
        if not os.path.isfile(config):
            raise IOError("config file %s does not exist." %
                          config)
        elif not os.access(config, os.R_OK):
            raise IOError("config file %s is not readable. "
                          "Please check permission." %
                          config)
        else:
            self._config_parser.read(config)

    def _get_value(self, section, key):
        """Get a single value by section and key

        @param section: section name
        @param key: key name
        @raise ConfigParser.NoSectionError: when the specified section does
            not exist
        @raise ConfigParser.NoOptionError: when the specified key does not

            exist
        """
        value = self._config_parser.get(section, key)
        if value == ['']:
            return ''
        else:
            return value.strip()

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
            return self._get_value(section, key)
        except configparser.Error as ex:
            logger.warn("ConfigReader, _get_value_with_default: %s" % ex)
            return default_value

    def _get_all_values_for_section(self, section):
        """Get all values for all the keys in the section"""
        value_list = list()
        pairs = self._config_parser.items(section)
        for item in pairs:
            value_list.append(item[1])
        return value_list

