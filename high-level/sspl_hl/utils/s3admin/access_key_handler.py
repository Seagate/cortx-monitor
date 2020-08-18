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
