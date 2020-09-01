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
PLEX data provider for getting Halon response messages.
"""

# Third party
import threading
import json

import time
from twisted.internet import reactor
from twisted.internet.task import deferLater

# PLEX
from plex.core import log

# Local
from plex.util.list_util import ensure_list
from sspl_hl.utils.rabbit_mq_utils import HalondConsumer
from sspl_hl.utils.base_castor_provider import BaseCastorProvider


class RMQException(Exception):

    """
    Rabbit MQ related exception
    """
    pass


class ResponseProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods

    """
    Class to support Halond response message consumption.
    """

    RESPONSE_POLLING_COUNT = 5

    def __init__(self, name, description):
        super(ResponseProvider, self).__init__(name, description)
        self.__message_dict = {}

    def on_create(self):
        """
        Implement this method to initialize the ResponseProvider.
        """
        super(ResponseProvider, self).on_create()
        ResponseProvider.run_async(
            self.consume_halon_messages, ()
        )

    @staticmethod
    def handle_success_response(result, request):
        """ Success handler for _check_and_get_data
        """
        if result:
            request.reply(ensure_list(result))
        else:
            request.responder.reply_exception(
                ensure_list("File System Status couldn't be retrieved")
            )

    @staticmethod
    def handle_error_response(error, request):
        """ Error Handler for _check_and_get_data
        """
        if error:
            request.responder.reply_exception(ensure_list(error))
        else:
            request.responder.reply_exception(
                ensure_list("Some error occurred")
            )

    def render_query(self, request):
        """ Render query for Response Provider
        """
        defer_res = deferLater(
            reactor,
            1,
            self._check_and_get_data,
            ResponseProvider.RESPONSE_POLLING_COUNT,
            request
        )
        defer_res.addCallback(
            ResponseProvider.handle_success_response, request)
        defer_res.addErrback(
            ResponseProvider.handle_error_response, request)

    def _check_and_get_data(self, count_down, request):
        """ Fetch data from response cache
        """
        poll_count = ResponseProvider.RESPONSE_POLLING_COUNT+1 - count_down
        time.sleep(poll_count)
        message_id = request.selection_args.get('messageId')
        self.log_info('Polling for Response. MSG_ID: {}. Re-try_Count: {}'
                      .format(message_id, poll_count))
        if message_id in self.__message_dict.keys():
            return json.dumps(self.__message_dict.get(message_id))
        elif count_down > 0:
            return self._check_and_get_data(count_down-1, request)
        else:
            err_msg = "File System Status couldn't be retrieved"
            err_reply = "Timed out while waiting for response" \
                        " with message=id :{} from halon".format(message_id)
            self.log_warning(err_reply)
            return err_msg

    def put_response_message(self, body):
        """
        Read the request extract message_id and put the response
        message to file with file name as message_id.

        @param body: message body consumed from rabbit-mq queue
        @type body: str

        @param msg_dict: response messages dict
        @type msg_dict: dict
        """
        log.info('Message received from sspl_hl_resp queue: {}'.
                 format(body))
        try:
            body_json = json.loads(body)
        except ValueError as mp_exception:
            log.info("Unable to parse message:{} IGNORE".format(mp_exception))
            return

        message = body_json.get('message')
        if not message:
            log.info("Invalid Msg: message key is missing. Msg: {}".
                     format(body_json))
            return
        response_id = message.get("responseId")
        if not response_id:
            log.info("Invalid Msg: response_id not found. Msg: {}".
                     format(message))
            return
        self.__message_dict[response_id] = message
        log.info("Updated message dict with:{}:{}".format(
            response_id,
            message)
        )

    def consume_halon_messages(self):
        """
        Consume the Halond response messages..
        """
        consumer = None
        try:
            consumer = HalondConsumer(
                None,
                self.put_response_message)
        except RMQException as rmq_except:
            log.error("Error creating consumer:{}".format(rmq_except))
            raise
        try:
            consumer.start_consuming()
        except RMQException as rmq_except:
            log.error("Error in start_consuming(): {}".format(rmq_except))
            raise

    @staticmethod
    def run_async(func, args):
        """
        run the func asynchronously.
        @param func: function to run in background.
        @type func: func

        @args: arguments to the function
        @type: list

        """
        resp_thread = threading.Thread(target=func, args=args)
        resp_thread.daemon = True
        resp_thread.start()


# pylint: disable=invalid-name, too-many-function-args
provider = ResponseProvider('response', 'Halond response Provider')
# pylint: enable=invalid-name
