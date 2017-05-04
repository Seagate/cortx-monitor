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
from sspl_hl.utils.s3admin.s3_utils import CommandResponse, execute_cmd


class AccountUtility():
    def __init__(self, client, args=None):
        """AccountUtility constructor.

        Name and email will be required for create operation.
        """

        self.client = client
        self.args = args
        #self.name = name
        #self.email = email

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
