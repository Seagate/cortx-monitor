"""
 ****************************************************************************
 Filename:          filestore.py
 Description:       Utility functions to deal with json data,
                    dump or load from file
 Creation Date:     01/16/2020
 Author:            Sandeep Anjara <sandeep.anjara@seagate.com>

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2019/06/11 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import os
import json
import pickle
from framework.utils.store import Store
from framework.utils.service_logging import logger

class FileStore(Store):

    def __init__(self):
        super(FileStore, self).__init__()

    def put(self, value, key):
        """ Dump value to given absolute file path"""

        # Check if directory exists
        absfilepath = key
        directory_path = os.path.join(os.path.dirname(absfilepath), "")
        if not os.path.isdir(directory_path):
            logger.critical("Path doesn't exists: {0}".format(directory_path))
            return

        try:
            fh = open(absfilepath,"wb")
            pickle.dump(value, fh)
        except IOError as err:
            errno, strerror = err.args
            logger.warn("I/O error[{0}] while dumping data to file {1}): {2}"\
                .format(errno,absfilepath,strerror))
        except Exception as gerr:
            logger.warn("Error[{0}] while dumping data to file {1}"\
                .format(gerr, absfilepath))
        else:
            fh.close()

    def get(self, key):
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
            value = pickle.load(fh)
        except IOError as err:
            errno, strerror = err.args
            logger.warn("I/O error[{0}] while loading data from file {1}): {2}"\
                .format(errno,absfilepath,strerror))
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
