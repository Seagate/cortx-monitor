"""
 ****************************************************************************
 Filename:          realstor_encl.py
 Description:       Handles messages for RealStor enclosure requests
 Creation Date:     11/08/2019
 Author:            Pranav Risbud

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import subprocess
import json
import calendar
import time
import socket

from actuators.impl.actuator import Actuator

from framework.base.debug import Debug
from framework.utils.service_logging import logger
from framework.utils import mon_utils

from framework.platforms.realstor.realstor_enclosure import singleton_realstorencl

class RealStorActuator(Actuator, Debug):
    """Handles request messages for Node server requests"""

    ACTUATOR_NAME = "RealStorActuator"
    SYSTEM_INFORMATION = "SYSTEM_INFORMATION"
    SITE_ID = "site_id"
    RACK_ID = "rack_id"
    NODE_ID = "node_id"

    REQUEST_GET = "ENCL"

    FRU_DISK = "disk"
    FRU_FAN = "fan"
    FRU_CONTROLLER = "controller"

    RESOURCE_ALL = "*"

    @staticmethod
    def name():
        """ @return: name of the module."""
        return RealStorActuator.ACTUATOR_NAME

    def __init__(self):
        super(RealStorActuator, self).__init__()

        self.rssencl = singleton_realstorencl

        self.request_fru_func = {
            self.REQUEST_GET: {
                self.FRU_DISK: self._get_disk,
                self.FRU_FAN: self._get_fan_modules,
                self.FRU_CONTROLLER: self._get_controllers
            }
        }

        self.fru_response_manipulators = {
            self.FRU_FAN: self.manipulate_fan_response,
            self.FRU_CONTROLLER: self._update_controller_response
        }

    def perform_request(self, jsonMsg):
        """Performs the RealStor enclosure request

        @return: The response string from performing the request
        """
        response = "N/A"
        try:
            enclosure_request = jsonMsg.get("actuator_request_type").get("storage_enclosure").get("enclosure_request")
            (request_type, enclosure, fru, fru_type) = [
                    s.strip() for s in enclosure_request.split(":")]
            resource = jsonMsg.get("actuator_request_type").get("storage_enclosure").get("resource")

            response = self.make_response(self.request_fru_func[request_type][fru_type](
                resource), fru_type, resource)

        except Exception as e:
            logger.exception("Error while getting details for JSON: {}".format(jsonMsg))
            response = {"Error": e}

        return response

    def make_response(self, fru_details, fru_type, resource_id):

        resource_type = "enclosure:fru:{}".format(fru_type)
        epoch_time = str(calendar.timegm(time.gmtime()))
        if socket.gethostname().find('.') >= 0:
            host_id = socket.gethostname()
        else:
            host_id = socket.gethostbyaddr(socket.gethostname())[0]

        alert_id = mon_utils.get_alert_id(epoch_time)

        if resource_id != self.RESOURCE_ALL:
            resource_id = self.fru_response_manipulators[fru_type](fru_details)

        response = {
          "alert_type":"GET",
          "severity":"informational",
          "host_id": host_id,
          "alert_id": alert_id,
          "info": {
            "site_id": self.rssencl.site_id,
            "rack_id": self.rssencl.rack_id,
            "node_id": self.rssencl.node_id,
            "cluster_id": self.rssencl.cluster_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "event_time": epoch_time
          },
          "specific_info": fru_details
        }

        return response

    def _get_disk(self, disk):
        """Retreive realstor disk info using cli api /show/disks"""

        # make ws request
        url = self.rssencl.build_url(
                  self.rssencl.URI_CLIAPI_SHOWDISKS)

        # TODO: Add pagination to response for '*' case.
        # PODS storage enclosures have will have
        # ~ 80 to 100 drives, which will make the
        # response huge.
        if(disk != self.RESOURCE_ALL):
            try:
                diskId = "0.{}".format(int(disk))
            except ValueError:
                msg = "Wrong format for disk resource value: {},"\
                        " expected int or '*'".format( disk)
                logger.error("RealStorActuator: _get_disk: {}".format(msg))
                return

            url = url + "/" + diskId

        url = url + "/detail"


        response = self.rssencl.ws_request( url, self.rssencl.ws.HTTP_GET)

        if not response:
            logger.warn("{0}:: Disks status unavailable as ws request {1}"
                " failed".format(self.rssencl.EES_ENCL, url))
            return

        if response.status_code != self.rssencl.ws.HTTP_OK:
            if url.find(self.rssencl.ws.LOOPBACK) == -1:
                logger.error("{0}:: http request {1} to poll disks failed with"
                    " err {2}".format(self.rssencl.EES_ENCL, url, response.status_code))
            return

        try:
            jresponse = json.loads(response.content)
        except ValueError as badjson:
            logger.error("%s returned mal-formed json:\n%s" % (url, badjson))

        if jresponse:
            api_resp = self.rssencl.get_api_status(jresponse['status'])

            if ((api_resp == -1) and
                   (response.status_code == self.rssencl.ws.HTTP_OK)):
                logger.warn("/show/disks api response unavailable, "
                    "marking success as http code is 200")
                api_resp = 0

            if api_resp == 0:
                drives = jresponse['drives']

                return drives

    def _get_fan_modules(self, instance_id):

        url = self.rssencl.build_url(
              self.rssencl.URI_CLIAPI_SHOWFANMODULES)

        response = self.rssencl.ws_request(
                        url, self.rssencl.ws.HTTP_GET)

        if not response:
            logger.warn("{0}:: Fan-modules status unavailable as ws request {1}"
                            "failed".format(self.rssencl.EES_ENCL, url))
            return

        if response.status_code != self.rssencl.ws.HTTP_OK:
            if url.find(self.rssencl.ws.LOOPBACK) == -1:
                logger.error(
                    "{0}:: http request {1} to get fan-modules failed with http err"
                    " {2}".format(self.rssencl.EES_ENCL, url, response.status_code))
            return

        response_data = json.loads(response.text)

        fan_modules_list = response_data["fan-modules"]
        fan_modules_list = self._get_fan_module_data(fan_modules_list, instance_id)
        return fan_modules_list

    def _get_fan_module_data(self, fan_modules_list, instance_id):

        fan_module_info_dict = {}
        fan_module_list = []

        for fan_module in fan_modules_list:
            if instance_id == self.RESOURCE_ALL:
                fan_module_info_dict = self._parse_fan_module_info(fan_module)
                logger.exception(fan_module_info_dict)
                fan_module_list.append(fan_module_info_dict)
            else:
                name = fan_module.get("name", None)
                if name is None:
                    continue
                slot = name.split(" ")[2]
                if slot == instance_id:
                    fan_module_info_dict = self._parse_fan_module_info(fan_module)
        if fan_module_list:
            return fan_module_list
        return fan_module_info_dict

    def _parse_fan_module_info(self, fan_module):
        fan_list = []
        fans = {}
        fan_key = ""

        fan_attribute_list = [ 'status', 'name', 'speed', 'durable-id',
            'health', 'fw-revision', 'health-reason', 'serial-number',
                'location', 'position', 'part-number', 'health-recommendation',
                    'hw-revision', 'locator-led' ]

        fru_fans = fan_module.get("fan", [])

        for fan in fru_fans:
            for fan_key in filter(lambda common_key: common_key in fan_attribute_list, fan):
                fans[fan_key] = fan.get(fan_key)
            fan_list.append(fans)

        fan_module_info_key_list = \
            ['name', 'location', 'status', 'health',
                'health-reason', 'health-recommendation', 'enclosure-id',
                'durable-id', 'position']

        fan_module_info_dict = {}

        for fan_module_key, fan_module_value in fan_module.items():
            if fan_module_key in fan_module_info_key_list:
                fan_module_info_dict[fan_module_key] = fan_module_value

        fan_module_info_dict["fans"] = fan_list
        return fan_module_info_dict

    def manipulate_fan_response(self, response):
        """Manipulate fan response dto change resource_id"""
        resource_id = None
        resource_id = response.get("name", None)
        return resource_id

    def _get_controllers(self, instance_id):

        url = self.rssencl.build_url(
              self.rssencl.URI_CLIAPI_SHOWCONTROLLERS)

        response = self.rssencl.ws_request(
                        url, self.rssencl.ws.HTTP_GET)

        if not response:
            logger.warn("{0}:: Controller status unavailable as ws request {1}"
                            "failed".format(self.rssencl.EES_ENCL, url))
            return

        if response.status_code != self.rssencl.ws.HTTP_OK:
            if url.find(self.rssencl.ws.LOOPBACK) == -1:
                logger.error(
                    "{0}:: http request {1} to get controller failed with http err"
                    " {2}".format(self.rssencl.EES_ENCL, url, response.status_code))
            return

        response_data = json.loads(response.text)

        controllers_list = response_data["controllers"]
        controllers_list = self._get_controller_data(controllers_list, instance_id)
        return controllers_list

    def _get_controller_data(self, controllers_list, instance_id):

        controller_info_dict = {}
        controller_list = []

        for controller in controllers_list:
            if instance_id == self.RESOURCE_ALL:
                controller_info_dict = controller
                controller_list.append(controller_info_dict)
            else:
                controller_id = controller.get("controller-id-numeric", None)
                if controller_id is None:
                    continue
                slot = str(controller_id)
                if slot == instance_id:
                    controller_info_dict = controller
        if controller_list:
            return controller_list
        return controller_info_dict

    def _update_controller_response(self, response):
        """Manipulate controller response dto change resource_id"""
        resource_id = None
        resource_id = response.get("durable-id", None)
        return resource_id
