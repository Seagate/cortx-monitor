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

"""
 ****************************************************************************
  Description:       Utility functions to deal with json data,
                    dump or load from file
 ****************************************************************************
"""
import os
import errno
import json
import pickle
from configparser import ConfigParser
from framework.utils.store import Store
from framework.utils.service_logging import logger

class FileStore(Store):

    def __init__(self):
        super(FileStore, self).__init__()
        self.config_parser = ConfigParser()

    def read(self, config_path=None):
        if config_path is None:
            logger.error("config path can't be empty for filestore config operations")
            return None
        if config_path is not None and isinstance(config_path, str):
            self.config_parser.read(config_path)
        elif config_path is not None and isinstance(config_path, dict):
            self.config_parser.read_dict(config_path)
        else:
            logger.error("config path can be either filepath or dict for filestore config operations")

    def put(self, value, key, pickled=True):
        """ Dump value to given absolute file path"""

        absfilepath = key
        directory_path = os.path.join(os.path.dirname(absfilepath), "")

        # If directory does not exists, create
        if not os.path.isdir(directory_path):
            try:
                os.makedirs(directory_path, exist_ok=True)
                os.chown(directory_path, 'sspl-ll', 'sspl-ll')
            except OSError as exc:
                if exc.errno == errno.EACCES:
                    logger.critical(f"Permission denied while creating dir: {directory_path}")
            except Exception as err:
                    logger.warn(f"{directory_path} creation failed with error {err}, alerts \
                    may get missed on sspl restart or failover!!")

        try:
            fh = open(absfilepath,"wb")
            if pickled:
                pickle.dump(value, fh)
            else:
                fh.write(value)

        except IOError as err:
            logger.warn("I/O error[{0}] while dumping data to file {1}): {2}"\
                .format(err.errno,absfilepath,err))
        except Exception as gerr:
            logger.warn("Error[{0}] while dumping data to file {1}"\
                .format(gerr, absfilepath))
        else:
            fh.close()

    def get(self, key, option=None):
        """
        key: abs path of file in case to load any json object and section of ini in case of loading any config
        option: section's option
        e.g. for config we can use: store.get('SYSTEM_INFORMATION', 'operating_system')
        e.g. to get cache or to load files we can use: store.get('file_path_to_load')
        """
        if option:
            return self.config_parser.get(key, option)
        else:
            return self._load_json_file(key)

    def items(self, section):
        """
        overridden from config parser to make look and feel like same
        """
        return self.config_parser.items(section)

    def _load_json_file(self, key):
        """ Load dict obj from json in given absolute file path"""
        value = None
        absfilepath = key

        # Check if directory exists
        directory_path = os.path.join(os.path.dirname(absfilepath), "")
        if not os.path.isdir(directory_path):
            logger.critical("Path doesn't exists: {0}".format(directory_path))
            return

        try:
            fh = open(absfilepath,"rb")
            try:
                value = pickle.load(fh)
            except:
                value = fh.read()
        except IOError as err:
            logger.warn("I/O error[{0}] while loading data from file {1}): {2}"\
                .format(err.errno,absfilepath,err))
        except ValueError as jsonerr:
            logger.warn("JSON error{0} while loading from {1}".format(jsonerr, absfilepath))
            value = None
        except OSError as oserr:
            logger.warn("OS error{0} while loading from {1}".format(oserr, absfilepath))
        except Exception as gerr:
            logger.warn("Error{0} while reading data from file {1}"\
                .format(gerr, absfilepath))
        else:
            fh.close()

        return value

    def exists(self, key):
        """check if key is present
        """
        key_present = False
        status = "Failure"
        try:
            key_present = os.path.exists(key)
            status = "Success"
        except Exception as gerr:
            logger.warn("Error while checking if {0} is present".format(gerr))

        return key_present, status

    def delete(self, key):
        """ delete a file
        """
        if os.path.exists(key):
            os.remove(key)

    def get_keys_with_prefix(self, prefix):
        """ get keys with given prefix
        """
        if not os.path.exists(prefix):
            return []
        else:
            return os.listdir(prefix)

if __name__ == '__main__':
    store = FileStore()
    store.read('/etc/sspl.conf')
    print(store.get('SYSTEM_INFORMATION', 'setup'))
