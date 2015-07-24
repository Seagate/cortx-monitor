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
    MESSAGE_ID_KEY = "messageId"

    def __init__(self, message_id=get_uuid_in_str()):
        self.message_id = message_id

    def to_dict(self):
        """
        Get the Halon message in dict

        @return: returns the Halon message.
        @rtype: dict
        """
        return {Message.MESSAGE_ID_KEY: self.message_id}


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
    SERVICE_REQUEST_KEY = "serviceRequest"
    COMMAND_KEY = "command"
    NODE_KEY = "node"

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
    STATUS_REQUEST_KEY = "statusRequest"
    ENTITY_TYPE_KEY = "entityType"
    ENTITY_FILTER_KEY = "entityFilter"

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
    STATUS_RESPONSE_KEY = "statusResponse"
    ENTITY_ID_KEY = "entityId"
    RESPONSE_ID_KEY = "responseId"
    ENTITY_NAME_KEY = "entityName"
    STATUS_KEY = "status"
    ITEMS_KEY = "items"

    def __init__(self):
        self.status_response = CommandResponse()


class NodeStatusRequest(StatusRequest):
    # pylint: disable=too-few-public-methods
    """
    This class defines the Status command for Halon node
    """

    def __init__(self):
        super(NodeStatusRequest, self).__init__()

    def get_request_message(self, entity_type, entity_filter=None):
        """
        Get the Halon node command status request message in JSON string
        @param entity_type: The type of entity in CaStor system i.e. cluster
        or node.
        @type entity_type: str

        @return: Halon node command status request message in string.
        @rtype: str
        """
        message = {
            StatusRequest.STATUS_REQUEST_KEY: {
                StatusRequest.ENTITY_TYPE_KEY: entity_type,
                StatusRequest.ENTITY_FILTER_KEY: entity_filter}}
        self.status_request.message.update(message)
        return self.status_request.__dict__


class NodeStatusResponse(StatusResponse):
    # pylint: disable=too-few-public-methods
    """
    This class is for emulating the Mock node Status command response from
    Halon.
    In future we can enhance this to parse the Halon Status response.

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
        super(NodeStatusResponse, self).__init__()

    @staticmethod
    def _get_response_items(entity_type='node'):
        """
        Get the mocked entity items for Halon node status command response
        @param entity_type: The type of entity in CaStor system i.e. cluster
        or node.
        @type entity_type: str


        @return: Halon node command status response items list.
        @rtype: list
        """
        items = []
        for item_name in range(1, NodeStatusResponse.NO_OF_CLUSTERS):
            item = {
                StatusResponse.ENTITY_ID_KEY: get_uuid_in_str(),
                StatusResponse.STATUS_KEY: random.choice(
                    NodeStatusResponse.ENTITY_STATUS),
                StatusResponse.ENTITY_NAME_KEY: '{}00{}'.format(
                    entity_type,
                    item_name)}
            items.append(item)
        return items

    def get_response_message(self, entity_type):
        """
        Get the Halon node command status response message in JSON string
        @param entity_type: The type of entity in CaStor system i.e. cluster
        or node.
        @type entity_type: str

        @param entity_filter: The filter expression to filter the entities in
        CaStor system
        @type entity_filter: str

        @return: Halon node command status response message in string.
        @rtype: str
        """

        items = self._get_response_items(entity_type)
        message = {
            StatusResponse.STATUS_RESPONSE_KEY: {
                StatusResponse.RESPONSE_ID_KEY: get_uuid_in_str(),
                StatusResponse.ITEMS_KEY: items}}
        self.status_response.message.update(message)
        return self.status_response.__dict__


class NodeServiceRequest(ServiceRequest):
    # pylint: disable=too-few-public-methods

    """
        Service request for node
    """
    def __init(self):
        super(NodeServiceRequest, self).__init__()

    def get_request_message(self, command, node=None):
        """
        Get the Halon node command service request message in JSON string
        @param command: The command for service [start, stop, etc.].
        @type command: str

        @return: Halon node command status request message.
        @rtype: dict
        """
        message = {
            ServiceRequest.SERVICE_REQUEST_KEY: {
                ServiceRequest.COMMAND_KEY: command,
                ServiceRequest.NODE_KEY: node}}
        self.service_request.message.update(message)
        return self.service_request.__dict__


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
    STATUS_RESPONSE_KEY = "rgResponse"
    ENTITY_ID_KEY = "entityId"
    RESPONSE_ID_KEY = "responseId"
    ENTITY_NAME_KEY = "entityName"
    STATUS_KEY = "status"
    ITEMS_KEY = "items"

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
                StatusResponse.ENTITY_ID_KEY: get_uuid_in_str(),
                StatusResponse.STATUS_KEY: random.choice(
                    HaResourceGraphResponse.ENTITY_STATUS),
                StatusResponse.ENTITY_NAME_KEY: '{}00{}'.format(
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
            StatusResponse.STATUS_RESPONSE_KEY: {
                StatusResponse.RESPONSE_ID_KEY: get_uuid_in_str(),
                StatusResponse.ITEMS_KEY: items}}
        self.status_response.message.update(message)
        return self.status_response.__dict__

    def parse_response_message(self):
        """
        Parse the Halon resource graph response and return information
        Note: Implement this function once Halon starts publishing the
              resource graph information.
        """
        pass


class ListResponse(object):
    # pylint: disable=too-few-public-methods
    """
    This class is for emulating the Mock Service list command response
    for Service listing.
    In future we can enhance this to parse the Service List response.

    Notes:
    1. Class level variables defined below with suffix "_key" are used
       to create message keys to map to language bindings defined in
       Service List message response.
    2. In future we can externalize these keys to configuration file.
    """
    SERVICE_RESPONSE_KEY = "serviceListResponse"
    SERVICE_NAME_KEY = "serviceName"
    PID_KEY = "pid"
    SERVICE_DESCRIPTION_KEY = "serviceDescription"
    LOAD_KEY = "load"
    ACTIVE_KEY = "active"
    SUB_KEY = "sub"
    RESPONSE_ID_KEY = "responseId"
    ITEMS_KEY = "items"
    ENTITY_NAME_KEY = "entityName"
    ENTITY_TYPE_KEY = "entityType"
    ENTITY_ID_KEY = "entityId"

    def __init__(self):
        self.list_response = CommandResponse()


class ServiceListResponse(ListResponse):
    # pylint: disable=too-few-public-methods
    """
    This class is for emulating the Mock service list command response
    from Halon.
    In future we can enhance this to parse the service list response.

    Notes:
    1. Class level variables defined below with suffix "_key" are used
       to create message keys to map to language bindings defined in
       Service list message response.
    2. In future we can externalize these keys to configuration file.
    """
    NO_OF_SERVICES = 4
    SERVICE_NAMES = [
        'crond',
        'plex',
        'halon',
        'docker'
    ]
    LOAD_STATUS = [
        "loaded",
        "failed"
    ]
    ACTIVE_STATUS = [
        "active",
        "failed"
    ]
    SUB_STATUS = [
        "waiting",
        "mounted",
        "running",
        "plugged",
        "exited"
    ]

    def __init__(self):
        super(ServiceListResponse, self).__init__()

    @staticmethod
    def _get_response_items():
        """
        Get the mocked entity items for service list command response

        @return: service list command items list.
        @rtype: list
        """
        items = []
        for item_name in range(1, ServiceListResponse.NO_OF_SERVICES):
            item = {
                ListResponse.SERVICE_NAME_KEY: random.choice(
                    ServiceListResponse.SERVICE_NAMES),
                ListResponse.PID_KEY: random.randint(
                    1,
                    9),
                ListResponse.SERVICE_DESCRIPTION_KEY: "some description{}"
                                                      .format(item_name),
                ListResponse.LOAD_KEY: random.choice(
                    ServiceListResponse.LOAD_STATUS),
                ListResponse.ACTIVE_KEY: random.choice(
                    ServiceListResponse.ACTIVE_STATUS),
                ListResponse.SUB_KEY: random.choice(
                    ServiceListResponse.SUB_STATUS),
                ListResponse.ENTITY_NAME_KEY: random.choice(
                    ['c{}'.format(item_name), 'n{}'.format(item_name)]),
                ListResponse.ENTITY_TYPE_KEY: random.choice(
                    ['cluster', 'node']),
                ListResponse.ENTITY_ID_KEY: get_uuid_in_str()
                }
            items.append(item)
        return items

    def get_response_message(self):
        """
        Get the list response message.
        """
        items = self._get_response_items()
        message = {
            ListResponse.SERVICE_RESPONSE_KEY: {
                ListResponse.RESPONSE_ID_KEY: get_uuid_in_str(),
                ListResponse.ITEMS_KEY: items
            }
        }
        self.list_response.message.update(message)
        return self.list_response.__dict__
