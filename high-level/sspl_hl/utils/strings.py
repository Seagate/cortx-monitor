# Copyright (c) 2017 Seagate Technology LLC and/or its Affiliates
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
    S3_SERVICE = "s3"
    NO_SUCH_ENTITY = "NoSuchEntity"
    ENTITY_EXISTS = "EntityAlreadyExists"
    INVALID_ACCESS_KEY = "InvalidAccessKeyId"
    QUOTA_EXCEEDED = "AccessKeyQuotaExceeded"
    SIGNATURE_NOT_MATCH = "SignatureDoesNotMatch"
    CONNECTION_ERROR = "ConnectionError"
    DELETE_CONFLICT = "DeleteConflict"
    SERVICE_UNAVAILABLE = "ServiceUnavailable"

    BUCKETS_AVAILABLE_ERROR = "Account can not be deleted." \
                              " Please remove all Buckets associated with " \
                              "Account."


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
