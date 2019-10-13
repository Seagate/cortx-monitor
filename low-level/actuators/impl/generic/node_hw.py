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
 prohibited. All other rights are expressly reserved by Seagate Technology,
 LLC.
 ****************************************************************************
"""
import abc
import subprocess

from actuators.impl.actuator import Actuator
from framework.base.debug import Debug
from framework.utils.service_logging import logger


class NodeHWactuator(Actuator, Debug):
    """Handles request messages for Node server requests
    """

    ACTUATOR_NAME = "NodeHWactuator"

    @staticmethod
    def name():
        """ @return: name of the module."""
        return NodeHWactuator.ACTUATOR_NAME

    def __init__(self, executer):
        super(NodeHWactuator, self).__init__()
        self.sensor_id_map = None
        self._executer = executer

    def initialize(self):
        """Performs basic Node HW actuator initialization"""

        # self._executer.get_fru_list_by_type(['fan', 'psu'])

    def perform_request(self, json_msg):
        """Performs the Node server request

        @return: The response string from performing the request
        """
        response = ""
        node_request = json_msg.get("node_controller")
        fru = node_request.get("node_request").split(":")[2]
        fru_instance = node_request.get("resource")

        return response
