# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2017 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.
# _author_ = "Vikram chhajer"

import json

import xmltodict
import plex.core.log as logger

from sspl_hl.utils.strings import Strings, Status
from sspl_hl.utils.s3admin.s3_utils import CommandResponse, execute_cmd, \
    sign_request_v2


class AccountUtility():
    def __init__(self, client, args=None):
        """AccountUtility constructor.

        Name and email will be required for create operation.
        """

        self.client = client
        self.args = args
        # self.name = name
        # self.email = email

    def list(self):
        """
        Handles account list operation
        """

        parameters = {'Action': Strings.LIST_ACCOUNTS}
        try:
            response, data = execute_cmd(self.client, parameters)
            if response.status == Status.OK_STATUS:
                account_response = json.loads(
                    json.dumps(xmltodict.parse(data)))
                accounts = \
                    account_response['ListAccountsResponse'][
                        'ListAccountsResult'][
                        'Accounts']
                temp_account_response = CommandResponse(response.status,
                                                        accounts)
                return temp_account_response
            else:
                temp_account_response = CommandResponse(response.status, None)
                return temp_account_response

        except Exception as ex:
            status = -1
            if type(ex) == Strings.CONNECTION_ERROR:
                status = Status.SERVICE_UNAVAILABLE
            temp_account_response = CommandResponse(status=status, msg=str(ex))
            return temp_account_response

    def create(self):
        """
        Handles account creation operation.
        """
        name = self.args.get("name", None)
        email = self.args.get("email", None)
        logger.info("Inside create command")
        parameters = {'Action': 'CreateAccount',
                      'AccountName': name,
                      'Email': email}
        try:
            response, data = execute_cmd(self.client, parameters)
            if response.status == Status.CREATED_STATUS:
                account_response = json.loads(
                    json.dumps(xmltodict.parse(data)))
                account = \
                    account_response['CreateAccountResponse'][
                        'CreateAccountResult'][
                        'Account']
                temp_account_response = CommandResponse(
                    response.status, account)
                return temp_account_response
            else:
                logger.info("Status  %s " % response.status)
                temp_account_response = CommandResponse(response.status, None)
                return temp_account_response
        except Exception as ex:
            logger.info("Exception %s " % str(ex))
            status = -1
            if type(ex) == Strings.CONNECTION_ERROR:
                status = Status.SERVICE_UNAVAILABLE
            temp_account_response = CommandResponse(status=status, msg=str(ex))
            return temp_account_response

    def remove(self):
        """
        Handles Account remove operation
        :return:
        """
        logger.info("Inside Remove command ")

        access_key = self.args.get("access_key", None)
        secret_key = self.args.get("secret_key", None)

        from sspl_hl.utils.s3admin.s3_utils import get_client

        s3_client, response = get_client(access_key, secret_key,
                                         Strings.S3_SERVICE)
        # First check if buckets are available for this account or not.
        logger.info("Check if buckets are associated with Account")
        try:
            if s3_client is None:
                # No S3 Client available.
                temp_account_response = CommandResponse(msg=response.msg,
                                                        status=response.status)
                return temp_account_response
            else:
                is_bucket_avail = self.is_buckets_available(s3_client)
                if is_bucket_avail:
                    status = -1
                    temp_account_response = CommandResponse(
                        status=status, msg=Strings.BUCKETS_AVAILABLE_ERROR)
                    return temp_account_response

        except Exception as ex:
            status = -1
            command_output = "{}".format(str(ex))
            try:
                logger.info("command_output %s " % command_output)
                if ex.response['Error']['Code'] == Strings.INVALID_ACCESS_KEY:
                    status = Status.UNAUTHORIZED
                elif ex.response['Error']['Code'] \
                        == Strings.SERVICE_UNAVAILABLE:
                    status = Status.SERVICE_UNAVAILABLE
                response = CommandResponse(status=status, msg=command_output)
            except Exception:
                response = CommandResponse(status=status, msg=command_output)
            return response

        # Buckets are not available.
        force = self.args.get("force", None)
        name = self.args.get("name", None)
        headers = {"content-type": "application/x-www-form-urlencoded",
                   "Accept": "text/plain"}
        parameters = {'Action': 'DeleteAccount',
                      'AccountName': name}
        parameters['force'] = force
        auth_header = sign_request_v2(access_key, secret_key,
                                      'POST', '/', {}, headers)
        headers['Authorization'] = auth_header

        try:
            response, data = execute_cmd(self.client, parameters, headers)
            logger.info("Account Remove response: [%s] " % response.status)
            if response.status == Status.OK_STATUS:
                account_response = json.loads(
                    json.dumps(xmltodict.parse(data)))
                temp_account_response = CommandResponse(
                    status=response.status)
                return temp_account_response
            else:
                account_response = json.loads(
                    json.dumps(xmltodict.parse(data)))['ErrorResponse']
                if account_response is None:
                    temp_account_response = CommandResponse(
                        response.status, None)
                    return temp_account_response
                status = -1
                if account_response['Error']['Code'] == \
                        Strings.NO_SUCH_ENTITY:
                    status = Status.NOT_FOUND
                elif account_response['Error']['Code'] == \
                        Strings.SIGNATURE_NOT_MATCH:
                    status = Status.UNAUTHORIZED
                elif account_response['Error']['Code'] == \
                        Strings.DELETE_CONFLICT:
                    status = Status.CONFLICT_STATUS
                temp_account_response = CommandResponse(status=status)
                return temp_account_response
        except Exception as ex:
            logger.info("Exception %s " % str(ex))
            status = -1
            if type(ex) == Strings.CONNECTION_ERROR:
                status = Status.SERVICE_UNAVAILABLE
            temp_account_response = CommandResponse(
                status=status, msg=str(ex))
            return temp_account_response

    def is_buckets_available(self, client):
        """
        check if any buckets are associated with Account
        """
        response = client.list_buckets()
        buckets = response['Buckets']
        logger.info("Checking if buckets available %s " % buckets)

        for bucket in buckets:
            if bucket['Name'] is not None:
                logger.info("Buckets are associated with account")
                return True
            else:
                return False
