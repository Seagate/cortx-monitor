#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
PLEX data provider for getting Halon response messages.
"""

# Third party
import threading
import json
from twisted.internet import reactor

# PLEX
from plex.core import log

# Local
from sspl_hl.utils.rabbit_mq_utils import HalondConsumer, find_key
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

    def __init__(self, name, description):
        super(ResponseProvider, self).__init__(name, description)
        self.__message_dict = {}

    def on_create(self):
        """
        Implement this method to initialize the ResponseProvider.
        """
        super(ResponseProvider, self).on_create()
        ResponseProvider.run_async(
            self.consume_halon_messages, ())

    def _query(self, selection_args, responder):

        message_id = selection_args['messageId']
        if message_id in self.__message_dict.keys():
            reactor.callFromThread(
                responder.reply, data=[
                    json.dumps(
                        self.__message_dict.get(message_id))])
        else:
            reactor.callFromThread(responder.reply_no_match)

    def put_response_message(self, body):
        """
        Read the request extract message_id and put the response
        message to file with file name as message_id.

        @param body: message body consumed from rabbit-mq queue
        @type body: str

        @param msg_dict: response messages dict
        @type msg_dict: dict
        """
        log.info("Updating the with:{}".format(body))
        try:
            body_json = json.loads(body)
            message = find_key(body_json, 'message')
            if not message:
                log.error('message key not found in \
                message body {}'.format(body_json))
                return
            response_id = find_key(message, "responseId")
            if not response_id:
                log.error('responseId key not found \
                in message body {}'.format(message))
                return
            log.debug(
                "Updated message dict with:{}:{}".format(
                    response_id,
                    message))
            self.__message_dict[response_id] = message
        except ValueError as mp_exception:
            log.debug("Unable to parse message:{} IGNORE".format(mp_exception))

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
