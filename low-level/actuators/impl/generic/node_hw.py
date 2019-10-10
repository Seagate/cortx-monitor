"""
 ****************************************************************************
 Filename:          node_hw.py
 Description:       Handles messages for Node server requests
 Creation Date:     10/10/2019
 Author:            Satish Darade

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import subprocess

from zope.interface import implements
from actuators.INode_hw import INodeHWactuator

from framework.base.debug import Debug
from framework.utils.service_logging import logger

class NodeHWactuator(Debug):
    """Handles request messages for Node server requests"""

    implements(INodeHWactuator)

    ACTUATOR_NAME = "NodeHWactuator"
    SUCCESS_MSG = "Success"
    ERROR_MSG = "Error" + ":{}"

    @staticmethod
    def name():
        """ @return: name of the module."""
        return NodeHWactuator.ACTUATOR_NAME

    def __init__(self):
        super(NodeHWactuator, self).__init__()

    def perform_request(self, jsonMsg):
        """Performs the Node server request

        @return: The response string from performing the request
        """
        response = ""

        return response
