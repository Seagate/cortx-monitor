"""
File contains the implementation of Halon message request and
response generator.
"""
# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2014 - 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.


import uuid
import datetime
import random

PLEX_PROVIDER_MSG_EXPIRES_IN_SEC = 3600

ERR_INVALID_RQ = "Error: Invalid request: Extra parameter '{extra}' detected"
ERR_INVALID_CMD = "Error: Invalid command: '{}'"
ERR_MISSING_CMD = "Error: Invalid request: Missing command"


def get_uuid_in_str():
    """
    Get the new uuid in string format.

    @return: new uuid in string format.
    @rtype: str
    """
    return str(uuid.uuid4())


class Message(object):
    # pylint: disable=too-few-public-methods

    """
    This class defines the Halon message construct.
    """
    message_id_key = "messageId"

    def __init__(self, message_id=get_uuid_in_str()):
        self.message_id = message_id

    def to_dict(self):
        """
        Get the Halon message in dict

        @return: returns the Halon message.
        @rtype: dict
        """
        return {Message.message_id_key: self.message_id}


class CommandRequest(object):
    # pylint: disable=too-few-public-methods

    """
    This class defines the Halon command request construct.
    """

    def __init__(self):
        self.username = "ignored_for_now"
        self.signature = "None"
        self.time = datetime.datetime.utcnow().isoformat() + '+00:00'
        self.expires = PLEX_PROVIDER_MSG_EXPIRES_IN_SEC
        self.message = Message().to_dict()


class CommandResponse(object):
    # pylint: disable=too-few-public-methods

    """
    This class is for emulating the Mock response from Halon.
    In future we can enhance this to parse the Halon Status response.
    """

    def __init__(self):
        self.username = "ignored_for_now"
        self.signature = "None"
        self.time = datetime.datetime.utcnow().isoformat() + '+00:00'
        self.expires = PLEX_PROVIDER_MSG_EXPIRES_IN_SEC
        self.message = Message().to_dict()


class ServiceRequest(object):
    # pylint: disable=too-few-public-methods

    """
    This class defines the Service command request to Halon.
    """

    def __init__(self):
        self.service_request = CommandRequest()


class StatusRequest(object):
    # pylint: disable=too-few-public-methods

    """
    This class defines the Status command request to Halon.

    Notes:
    1. class level variables defined below with suffix _key are used
       to create message keys to map to language bindings defined in
       Halon message response
    2. In future we can externalize these keys to configuration file.
    """
    status_request_key = "statusRequest"
    entity_type_key = "entityType"
    entity_filter_key = "entityFilter"

    def __init__(self):
        self.status_request = CommandRequest()


class StatusResponse(object):
    # pylint: disable=too-few-public-methods

    """
    This class is for emulating the Mock Status command response from Halon.
    In future we can enhance this to parse the Halon Status response.

    Notes:
    1. Class level variables defined below with suffix "_key" are used
       to create message keys to map to language bindings defined in
       Halon message response.
    2. In future we can externalize these keys to configuration file.
    """
    status_response_key = "statusResponse"
    entity_id_key = "entityId"
    response_id_key = "responseId"
    entity_name_key = "entityName"
    status_key = "status"
    items_key = "items"

    def __init__(self):
        self.status_response = CommandResponse()


class ResourceGraphResponse(object):
    # pylint: disable=too-few-public-methods

    """
    This class is for emulating the Mock resource graph command response
    from Halon.
    In future we can enhance this to parse the Halon resource graph response.

    Notes:
    1. Class level variables defined below with suffix "_key" are used
       to create message keys to map to language bindings defined in
       Halon message response.
    2. In future we can externalize these keys to configuration file.
    """
    status_response_key = "rgResponse"
    entity_id_key = "entityId"
    response_id_key = "responseId"
    entity_name_key = "entityName"
    status_key = "status"
    items_key = "items"

    def __init__(self):
        self.status_response = CommandResponse()


class HaResourceGraphResponse(StatusResponse):
    # pylint: disable=too-few-public-methods

    """
    This class is for emulating the Mock Halon resource graph command response
    from Halon.
    In future we can enhance this to parse the Halon resource graph response.

    Notes:
    1. Class level variables defined below with suffix "_key" are used
       to create message keys to map to language bindings defined in
       Halon message response.
    2. In future we can externalize these keys to configuration file.
    """
    NO_OF_CLUSTERS = 3
    NO_OF_NODES = 3
    ENTITY_STATUS = [
        'running',
        'stopped',
        'idle',
        'starting',
        'dead',
        'active']

    def __init__(self):
        StatusResponse.__init__(self)

    @staticmethod
    def _get_response_items(entity_type='cluster'):
        """
        Get the mocked entity items for Halon resource graph command response
        @param entity_type: The type of entity in CaStor system
                            i.e. cluster or node.
        @type entity_type: str


        @return: Halon ha command status response items list.
        @rtype: list
        """
        items = []
        for item_name in range(1, HaResourceGraphResponse.NO_OF_CLUSTERS):
            item = {
                StatusResponse.entity_id_key: get_uuid_in_str(),
                StatusResponse.status_key: random.choice(
                    HaResourceGraphResponse.ENTITY_STATUS),
                StatusResponse.entity_name_key: '{}00{}'.format(
                    entity_type,
                    item_name)}
            items.append(item)
        return items

    def get_response_message(self, entity_type='cluster'):
        """
        Get the Halon resource graph response message
        @param entity_type: The type of entity in CaStor system
                            i.e. cluster or node.
        @type entity_type: str


        @return: Halon ha command status response message dict.
        @rtype: dict
        """

        items = self._get_response_items(entity_type)
        message = {
            StatusResponse.status_response_key: {
                StatusResponse.response_id_key: get_uuid_in_str(),
                StatusResponse.items_key: items}}
        self.status_response.message.update(message)
        return self.status_response.__dict__

    def parse_response_message(self):
        """
        Parse the Halon resource graph response and return information
        Note: Implement this function once Halon starts publishing the
              resource graph information.
        """
        pass
