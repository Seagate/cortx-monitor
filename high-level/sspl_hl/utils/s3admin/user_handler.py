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
from botocore.exceptions import ClientError

from sspl_hl.utils.strings import Strings, Status
from sspl_hl.utils.s3admin.s3_utils import CommandResponse


class UsersUtility():
    def __init__(self, client, args):
        """
        UserUtility Constructor
        """

        self.client = client
        self.args = args

    def list(self):
        """
        Handles user list operation.
        """

        user_args = {}
        try:
            logger.info("Inside list command")
            result = self.client.list_users(**user_args)
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
        Handle user modify operation.
        """
        user_args = {}
        logger.info("Inside modify command")
        user_args['UserName'] = self.args.get("name", None)
        user_args['NewUserName'] = self.args.get("new_name", None)
        path = self.args.get("path", None)
        if path is not None:
            user_args['NewPath'] = path

        try:
            result = self.client.update_user(**user_args)
            metadata = result.get('ResponseMetadata')
            if metadata is not None:
                status = metadata.get('HTTPStatusCode')
                response = CommandResponse(status, result)
                logger.info("User modified successfully")
            else:
                response = self.response_generator("No Response received.")
        except ClientError as ex:
            response = self.response_generator(ex)

        return response

    def remove(self):
        """
        Handle user remove operation.
        """
        user_args = {}
        user_args['UserName'] = self.args.get("name", None)
        try:
            result = self.client.delete_user(**user_args)
            metadata = result.get('ResponseMetadata')
            if metadata is not None:
                status = metadata.get('HTTPStatusCode')
                response = CommandResponse(status, result)
                logger.info("User removed successfully")
            else:
                response = self.response_generator("No Response received.")

        except Exception as ex:
            response = self.response_generator(ex)
        return response

    def create(self):
        """
        Handle user create operation.
        """
        user_args = {}
        user_args['UserName'] = self.args.get("name", None)
        path = self.args.get("path", None)
        if path is not None:
            user_args['Path'] = path

        try:
            result = self.client.create_user(**user_args)
            metadata = result.get('ResponseMetadata')
            if metadata is not None:
                status = metadata.get('HTTPStatusCode')
                response = CommandResponse(status, result)
                logger.info("User created successfully")
            else:
                response = self.response_generator("No Response received.")
        except ClientError as e:
            response = self.response_generator(e)
        except Exception as ex:
            logger.info("Exception %s " % str(ex))
            status = -1
            if type(ex) == Strings.CONNECTION_ERROR:
                status = Status.SERVICE_UNAVAILABLE
            response = CommandResponse(status=status, msg=str(ex))

        logger.info("Returning user create operation response.")
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
            response = CommandResponse(status=status, msg=command_output)
        except Exception as ex:
            response = CommandResponse(status=status, msg=command_output)
        return response
