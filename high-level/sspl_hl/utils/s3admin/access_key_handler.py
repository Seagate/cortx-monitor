# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2017 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.
# _author_ = "Vikram chhajer"

import plex.core.log as logger
from sspl_hl.utils.s3admin.s3_utils import CommandResponse
from sspl_hl.utils.strings import Strings, Status


class AccessKeyUtility():
    def __init__(self, client, args):
        """
        AccessKeyUtility Constructor
        """
        self.client = client
        self.args = args

    def list(self):
        """
        Handle access key list operation.
        """
        access_key_args = {}
        access_key_args['UserName'] = self.args.get("user_name", None)

        try:
            result = self.client.list_access_keys(**access_key_args)
            metadata = result.get('ResponseMetadata')
            if metadata is not None:
                status = metadata.get('HTTPStatusCode')
                response = CommandResponse(status, result)
            else:
                response = self.response_generator("No Response received.")

        except Exception as ex:
            response = self.response_generator(ex)
        return response

    def modify(self):
        """
        Handle access key modify operation.
        """
        access_key_args = {}
        access_key_args['UserName'] = self.args.get("user_name", None)
        access_key_args['AccessKeyId'] = self.args.get("user_access_key", None)
        access_key_args['Status'] = self.args.get("status", None)
        try:
            result = self.client.update_access_key(**access_key_args)
            metadata = result.get('ResponseMetadata')
            if metadata is not None:
                status = metadata.get('HTTPStatusCode')
                response = CommandResponse(status, result)
            else:
                response = self.response_generator("No Response received.")
        except Exception as ex:
            response = self.response_generator(ex)
        return response

    def remove(self):
        """
        Handle access key remove operation.
        """
        access_key_args = {}
        access_key_args['UserName'] = self.args.get("user_name", None)
        access_key_args['AccessKeyId'] = self.args.get("user_access_key", None)

        try:
            result = self.client.delete_access_key(**access_key_args)
            metadata = result.get('ResponseMetadata')
            if metadata is not None:
                status = metadata.get('HTTPStatusCode')
                response = CommandResponse(status, result)
            else:
                response = self.response_generator("No Response received.")
        except Exception as ex:
            response = self.response_generator(ex)
        return response

    def create(self):
        """
        Handle access key create operation.
        """

        access_key_args = {}
        access_key_args['UserName'] = self.args.get("user_name", None)

        try:
            result = self.client.create_access_key(**access_key_args)
            metadata = result.get('ResponseMetadata')
            if metadata is not None:
                status = metadata.get('HTTPStatusCode')
                response = CommandResponse(status, result)
            else:
                response = self.response_generator("No Response received.")
        except Exception as ex:
            response = self.response_generator(ex)
        return response

    def response_generator(self, ex):
        """
        Handle exception raised in all operations.

        It will return object with proper error code, which can be used in
        client to display proper error message.
        """

        status = -1
        command_output = "{}".format(str(ex))
        try:
            logger.info("Error code %s " % ex.response['Error']['Code'])
            if ex.response['Error']['Code'] == Strings.INVALID_ACCESS_KEY:
                status = Status.UNAUTHORIZED
            elif ex.response['Error']['Code'] == Strings.ENTITY_EXISTS:
                status = Status.CONFLICT_STATUS
            elif ex.response['Error']['Code'] == Strings.NO_SUCH_ENTITY:
                status = Status.NOT_FOUND
            elif ex.response['Error']['Code'] == Strings.SIGNATURE_NOT_MATCH:
                status = Status.UNAUTHORIZED
            elif ex.response['Error']['Code'] == Strings.QUOTA_EXCEEDED:
                status = Status.BAD_REQUEST
            response = CommandResponse(status=status, msg=command_output)
        except Exception as ex:
            response = CommandResponse(status=status, msg=command_output)
        return response
