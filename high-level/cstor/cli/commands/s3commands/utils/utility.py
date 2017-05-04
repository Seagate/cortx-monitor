#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
File containing utilities required for S3Admin command implementation
"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2017 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.

import os
import re
import urllib
import csv

from cstor.cli.commands.utils.strings import Strings
import cstor.cli.errors as errors

NAME_LENGTH = 64
EMAIL_LENGTH = 200
# regexp has two part : before@ and after@
# before@ : expression should not have @ or a whitespace before @
# after@  : validates expression like @abc.com, @abc.def.com
EMAIL_REGEXP = r'^[^@\s]+@[a-z0-9]+((([-.])([a-z0-9]+))+)?(\.[a-z0-9])?$'
NAME_REGEXP = r'^[^\W_]+(-[^\W_]+)?$'


class Status:
    STATUS = {'GOOD': 0,
              'INVALID_PERMISSION': 1,
              'FILE_NOT_FOUND': 2
              }


class AccountKeys:
    def __init__(self, parser):
        if parser.account_name is None:
            if parser.secret_key is None or parser.access_key is None:
                raise errors.InvalidArgumentError(Strings.ACCOUNT_ERROR)
            self.secret_key = parser.secret_key
            self.access_key = parser.access_key
        else:
            if parser.secret_key is not None or parser.access_key is not None:
                raise errors.InvalidArgumentError(Strings.ACCOUNT_ERROR)
            self.access_key, self.secret_key = get_account_keys(
                parser.account_name)

    def get_secret_key(self):
        return encode_key(self.secret_key)

    def get_access_key(self):
        return encode_key(self.access_key)


def _validate_regexp(value, length, regex, message, param):
    if value is not None and len(value) > length:
        raise errors.InvalidArgumentError("Invalid {}".format(param),
                                          u'Length of {} cannot be '
                                          u'greater than {} characters'
                                          .format(param, length))
    if value is not None and not re.match(regex, value):
        raise errors.InvalidArgumentError(message)
    return value


def _validate_email(value):
    """Validate email format.

    :param value: Email to validate.
    :return: email in success or raises InvalidArgumentError otherwise.
    """
    message = 'Invalid Email format "{0}".'.format(value)
    return _validate_regexp(value, EMAIL_LENGTH, EMAIL_REGEXP, message,
                            "Email")


def _validate_name(value):
    """Validate name format.

    :param value: Name to validate.
    :return: name in success or raises InvalidArgumentError otherwise.
    """
    message = 'Invalid Name format "{0}".'.format(value)
    return _validate_regexp(value, NAME_LENGTH, NAME_REGEXP, message, "Name")


def read_permissions(filepath):
    '''Checks the read permissions of the specified file'''
    try:
        os.access(filepath, os.R_OK)  # Find the permissions using os.access
    except IOError:
        return False

    return True


def is_file_available(filepath):
    if not os.path.isfile(filepath):
        return False
    return True


def encode_key(data):
    return urllib.quote(data, safe='')


def get_file_name(account_name):
    credential_dir = Strings.ENDPOINTS_CONFIG_FOLDER
    if not os.path.isdir(credential_dir):
        os.makedirs(credential_dir)
    file_name = credential_dir + \
        account_name.lower() + \
        Strings.CREDENTIAL_FILE_SUFFIX
    return file_name


def get_account_keys(account_name):
    file_name = get_file_name(account_name)
    if is_file_available(file_name):
        keys = csv_file_reader(file_name)
        return keys[0], keys[1]
    else:
        raise errors.InvalidArgumentError(
            "Unable to get Account secret key and access key for "
            "\'{}\'. Please enter manually.".format(
                account_name))


def populate_credential_file(name, data):
    try:
        file_name = get_file_name(name)
        return csv_file_writer(file_name, data)
    except Exception:
        print("")


def csv_file_writer(file_name, data):
    """
    Write data to a CSV file path
    """
    with open(file_name, "wb") as csv_file:
        os.chmod(file_name, 0o600)
        writer = csv.writer(csv_file, delimiter=',')
        for line in data:
            writer.writerow(line)
    return file_name


def csv_file_reader(file_obj):
    """
    Read a csv file
    """
    with open(file_obj, "rb") as f_obj:
        reader = csv.reader(f_obj)
        csvFileArray = []
        for row in reader:
            csvFileArray.append(row)
        return csvFileArray[1]
