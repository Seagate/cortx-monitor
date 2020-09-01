#!/usr/bin/python
# -*- coding: utf-8 -*-

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
File containing constant strings used across cstor
"""

import httplib


class Strings(object):
    PROVIDER = "s3admin"
    CREATE = "create"
    LIST = "list"
    MODIFY = "modify"
    REMOVE = "remove"
    ACCESS_KEY_ID = "Access key ID"
    SECRET_KEY_ID = "Secret access key"
    ACCESS_KEY = "access_key"
    SECRET_KEY = "secret_key"
    COMMUNICATION_ERROR = "Communication error"
    COMMUNICATION_ER_DESC = "Unable to reach Auth servers."
    SOCKET_ERROR = "socket error"
    ACCOUNT_ERROR = 'Either Account name or Secret key and Access key are ' \
                    'required.'
    ACCOUNT_REMOVE_ERROR = 'Secret key and Access key both are required.'
    ENDPOINTS_CONFIG_FOLDER = "/opt/data/.s3seagate/"
    CREDENTIAL_FILE_SUFFIX = "-accessKeys.csv"
    FILE_GENERATION_ERR = 'Unable to generate credential file.' \
                          'Please note down Access Key and Secret Key.'
    CAN_NOT_PERFORM = "Status: Can not perform.\nDetails: "
    STATUS = "status"


class Status(object):
    OK_STATUS = httplib.OK
    CREATED_STATUS = httplib.CREATED
    CONFLICT_STATUS = httplib.CONFLICT
    SERVICE_UNAVAILABLE = httplib.SERVICE_UNAVAILABLE
    NOT_FOUND = httplib.NOT_FOUND
    UNAUTHORIZED = httplib.UNAUTHORIZED
    BAD_REQUEST = httplib.BAD_REQUEST


class BaseHelpStr(object):
    """"""
    help = 'Default Help'


class UserHelpStr(BaseHelpStr):
    """Help string for User class"""
    help = 'Sub-Command to work with User mgmt interface. All the user mana' \
           'gement is done with the help of POSIX APIs'
    create = 'Creates a new POSIX User, of wheel group'
    remove = 'Removes the POSIX User and its associated permissions'
    force_remove = 'Forcing off may lead to unrevokable action. I know what' \
                   ' I am doing and I won\'t blame SeaGate for it'
    components = 'List of capabilities that the new user would need access to'
    name = 'Username of the new user'
    password = 'Password for the new user.'
