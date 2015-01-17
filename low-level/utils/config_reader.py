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
 All relevant license information (GPL, FreeBSD, etc)
 ****************************************************************************
"""

import os
import ConfigParser

from utils.service_logging import logger


class ConfigReader(object):
    """Configuration reader for notification sender""" 
    # Available exceptions from ConfigParser
    MissingSectionHeaderError   = ConfigParser.MissingSectionHeaderError
    NoSectionError              = ConfigParser.NoSectionError
    NoOptionError               = ConfigParser.NoOptionError
    Error                       = ConfigParser.Error

    def __init__(self, config):
        """Inializer for ConfigReader"""
        self._config_parser = ConfigParser.RawConfigParser()
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
            return self._config_parser.get(section, key)

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
            return values_from_config_parser.split(',')

    def _get_value_with_default(self, section, key, default_value):
        """helper function to read value with default function

        in case there is exception or incomplete configuration file
        we do provide default value for certain settings
        """
        try:
            return self._get_value(section, key)
        except ConfigParser.Error as ex:
            logger.warn("ConfigReader, _get_value_with_default: %s" % ex)
            return default_value

    def _get_all_values_for_section(self, section):
        """Get all values for all the keys in the section"""
        value_list = list()
        pairs = self._config_parser.items(section)
        for item in pairs:
            value_list.append(item[1])
        return value_list

    def _validate_all_general_settings(self):
        """This function to make sure config file contain all general settings

        Run through all public function above
        if any exception was being raise, then we have an invalid
        configuration file"""
        
#         try:
#             self.get_logging_level()
#                    
#         except ConfigParser.Error as err:
#             raise err

    # TODO: Validate config file and give user a friendly error message if it's corrupt or missing
    def validate_config_file(self):
        """This function validate the config file

        we only validate for the item we needed
        no redundancy has been checked"""
        self._validate_all_general_settings()


