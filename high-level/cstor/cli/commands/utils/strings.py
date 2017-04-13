#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
File containing constant strings used across cstor
"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.

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
    ENDPOINTS_CONFIG_FOLDER = "/opt/data/.s3seagate/"
    CREDENTIAL_FILE_SUFFIX = "-accessKeys.csv"
    FILE_GENERATION_ERR = 'Unable to generate credential file.' \
                          'Please note down Access Key and Secret Key.'
    CAN_NOT_PERFORM = "Status: Can not perform.\nDetails: "
    STATUS = "status"


class Status():
    OK_STATUS = httplib.OK
    CREATED_STATUS = httplib.CREATED
    CONFLICT_STATUS = httplib.CONFLICT
    SERVICE_UNAVAILABLE = httplib.SERVICE_UNAVAILABLE
    NOT_FOUND = httplib.NOT_FOUND
    UNAUTHORIZED = httplib.UNAUTHORIZED
    BAD_REQUEST = httplib.BAD_REQUEST
