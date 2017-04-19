# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2017 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.
# _author_ = "Vikram chhajer"
import httplib


class Strings():
    """
    Constant String initialization
    """
    CREATE = "create"
    REMOVE = "remove"
    MODIFY = "modify"
    LIST = "list"
    ENDPOINTS_CONFIG_PATH = "/etc/seagate/config/endpoints.yaml"
    LIST_ACCOUNTS = "ListAccounts"
    ACCESS_KEY = "access_key"
    SECRET_KEY = "secret_key"
    IAM_SERVICE = "iam"
    NO_SUCH_ENTITY = "NoSuchEntity"
    ENTITY_EXISTS = "EntityAlreadyExists"
    INVALID_ACCESS_KEY = "InvalidAccessKeyId"
    QUOTA_EXCEEDED = "AccessKeyQuotaExceeded"
    SIGNATURE_NOT_MATCH = "SignatureDoesNotMatch"
    CONNECTION_ERROR = "ConnectionError"


class Status():
    """
    Http status return codes initialization
    """
    OK_STATUS = httplib.OK
    CREATED_STATUS = httplib.CREATED
    NOT_FOUND = httplib.NOT_FOUND
    CONFLICT_STATUS = httplib.CONFLICT
    SERVICE_UNAVAILABLE = httplib.SERVICE_UNAVAILABLE
    UNAUTHORIZED = httplib.UNAUTHORIZED
    BAD_REQUEST = httplib.BAD_REQUEST
