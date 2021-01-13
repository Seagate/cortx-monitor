# Copyright (c) 2001-2020 Seagate Technology LLC and/or its Affiliates
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
 ****************************************************************************
  Description:       Handles messages for RealStor enclosure requests
 ****************************************************************************
"""
import json
import time
import socket

from actuators.impl.actuator import Actuator

from framework.base.debug import Debug
from framework.utils.service_logging import logger
from framework.utils import mon_utils
from framework.platforms.realstor.realstor_enclosure import singleton_realstorencl
from framework.base.sspl_constants import AlertTypes, SeverityTypes, ResourceTypes


class RealStorActuator(Actuator, Debug):
    """Handles request messages for Node server requests"""

    ACTUATOR_NAME = "RealStorActuator"
    SYSTEM_INFORMATION = "SYSTEM_INFORMATION"

    REQUEST_GET = "ENCL"

    FRU_DISK = "disk"
    FRU_FAN = "fan"
    FRU_CONTROLLER = "controller"

    RESOURCE_ALL = "*"

    FRU_PSU = "psu"
    FRU_SIDEPLANE = "sideplane"

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
                self.FRU_CONTROLLER: self._get_controllers,
                self.FRU_PSU:self._get_psu,
                self.FRU_SIDEPLANE:self._get_sideplane
            }
        }

        self.fru_response_manipulators = {
            self.FRU_FAN: self.manipulate_fan_response,
            self.FRU_DISK: self.update_disk_response,
            self.FRU_CONTROLLER: self._update_controller_response,
            self.FRU_PSU:self._update_psu_response,
            self.FRU_SIDEPLANE:self._update_sideplane_response
        }

    def perform_request(self, jsonMsg):
        """Performs the RealStor enclosure request

        @return: The response string from performing the request
        """
        response = "N/A"
        try:
            enclosure_request = jsonMsg.get("actuator_request_type").get("storage_enclosure").get("enclosure_request")
            (request_type, enclosure, component, component_type) = [
                    s.strip() for s in enclosure_request.split(":")]

            resource = jsonMsg.get("actuator_request_type").get("storage_enclosure").get("resource")
            if component == "fru":
                response = self.make_response(self.request_fru_func[request_type][component_type](
                    resource), component ,component_type, resource)
            elif component == "sensor":
                response = self.make_response(
                            self._get_sensor_data(sensor_type=component_type, sensor_name=resource),
                            component,
                            component_type,
                            resource)
            elif component == "interface":
                enclosure_type = enclosure_request.split(":")[2]
                if enclosure_type == ResourceTypes.INTERFACE.value:
                    response = self._handle_ports_request(enclosure_request, resource)
                else:
                    logger.error("Some unsupported interface passed, interface:{}".format(enclosure_type))
            elif component == "system":
                if component_type == 'info':
                    response = self.make_response(
                            self._get_system_info(),
                            component,
                            component_type,
                            resource)
                else:
                    logger.error("Unsupported system request :{}".format(component_type))

        except Exception as e:
            logger.exception("Error while getting details for JSON: {}".format(jsonMsg))
            response = {"Error": e}

        return response

    def make_response(self, component_details, component, component_type, resource_id):

        resource_type = "enclosure:{}:{}".format(component, component_type)
        epoch_time = str(int(time.time()))
        alert_id = mon_utils.get_alert_id(epoch_time)

        if component == "fru":
            if resource_id == self.RESOURCE_ALL:
                for comp in component_details:
                    comp['resource_id'] = self.fru_response_manipulators[
                                            component_type](comp if component_type!=self.FRU_DISK else [comp])
            else:
                resource_id = self.fru_response_manipulators[component_type](component_details)

        response = {
          "alert_type":"GET",
          "severity":"informational",
          "host_id": socket.getfqdn(),
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
          "specific_info": component_details
        }

        return response

    def _get_disk(self, disk):
        """Retreive realstor disk info using cli api /show/disks"""

        # make ws request
        url = self.rssencl.build_url(
                  self.rssencl.URI_CLIAPI_SHOWDISKS)

        # TODO: Add pagination to response for '*' case.
        # storage enclosures will have
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

            url = f"{url}/{diskId}"

        url = f"{url}/detail"


        response = self.rssencl.ws_request( url, self.rssencl.ws.HTTP_GET)

        if not response:
            logger.warn("{0}:: Disks status unavailable as ws request {1}"
                " failed".format(self.rssencl.LDR_R1_ENCL, url))
            return

        if response.status_code != self.rssencl.ws.HTTP_OK:
            if url.find(self.rssencl.ws.LOOPBACK) == -1:
                logger.error("{0}:: http request {1} to poll disks failed with"
                    " err {2}".format(self.rssencl.LDR_R1_ENCL, url, response.status_code))
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
                            "failed".format(self.rssencl.LDR_R1_ENCL, url))
            return

        if response.status_code != self.rssencl.ws.HTTP_OK:
            if url.find(self.rssencl.ws.LOOPBACK) == -1:
                logger.error(
                    "{0}:: http request {1} to get fan-modules failed with http err"
                    " {2}".format(self.rssencl.LDR_R1_ENCL, url, response.status_code))
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

    def update_disk_response(self, drives):
        """Manipulate disk response to get resource_id"""
        return drives[0].get("durable-id")

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
                            "failed".format(self.rssencl.LDR_R1_ENCL, url))
            return

        if response.status_code != self.rssencl.ws.HTTP_OK:
            if url.find(self.rssencl.ws.LOOPBACK) == -1:
                logger.error(
                    "{0}:: http request {1} to get controller failed with http err"
                    " {2}".format(self.rssencl.LDR_R1_ENCL, url, response.status_code))
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

    def _update_psu_response(self, response):
        """Manipulate controller response dto change resource_id"""
        resource_id = None
        resource_id = response.get("name", None)
        return resource_id

    def _update_sideplane_response(self, response):
        """Manipulate controller response to change resource_id"""
        resource_id = None
        resource_id = response.get("name", None)
        return resource_id

    def _get_sensor_data(self, sensor_type, sensor_name):
        """Retreive realstor sensor info using cli api /show/sensor-status"""
        sensor_response = self._get_encl_response(
                self.rssencl.URI_CLIAPI_SHOWSENSORSTATUS,
                self.rssencl.ws.HTTP_GET
        )
        if sensor_response:
            #TODO: optimize for specific sensor
            if sensor_name != self.RESOURCE_ALL:
                for sensor in sensor_response["sensors"]:
                    if sensor["sensor-name"] == sensor_name:
                        return sensor
                else:
                    return {}
            else:
                sensors = []
                for sensor in sensor_response["sensors"]:
                    if sensor["sensor-type"] == sensor_type.title():
                        sensor["resource_id"] = sensor["sensor-name"]
                        sensors.append(sensor)
                return sensors
        else:
            return {"error": "failed to get data from enclosure"}

    def _get_psu(self, psu_name):
        #build url for fetching the psu type data
        url = self.rssencl.build_url(
                      self.rssencl.URI_CLIAPI_SHOWPSUS)
        response = self.rssencl.ws_request( url, self.rssencl.ws.HTTP_GET)
        if not response:
            logger.warn("{0}: Psu status unavailable as ws request {1}"
                    " failed".format(self.rssencl.LDR_R1_ENCL, url))
            return
        if response.status_code != self.rssencl.ws.HTTP_OK:
            if url.find(self.rssencl.ws.LOOPBACK) == -1:
                logger.error("{0}:: http request {1} to poll psu failed with"
                        " err {2}".format(self.rssencl.LDR_R1_ENCL, url, response.status_code))
            return
        try:
            jresponse = json.loads(response.content)
        except ValueError as badjson:
            logger.error("%s returned mal-formed json:\n%s" % (url, badjson))
        if jresponse:
            api_resp = self.rssencl.get_api_status(jresponse['status'])
            if ((api_resp == -1) and
                    (response.status_code == self.rssencl.ws.HTTP_OK)):
                logger.warn("/show/power-supplies api response unavailable, "
                        "marking success as http code is 200")
                api_resp = 0
            if api_resp == 0:
                if psu_name == "*":
                    return jresponse["power-supplies"]
                else:
                    for resource in jresponse["power-supplies"]:
                        if psu_name == resource["name"]:
                            return resource
                    else:
                        raise Exception("Resource not Found")

    def _get_sideplane(self, sideplane_name):
        #build url for fetching the sideplane type data
        sideplane_expanders = []
        url = self.rssencl.build_url(
                      self.rssencl.URI_CLIAPI_SHOWENCLOSURE)
        response = self.rssencl.ws_request( url, self.rssencl.ws.HTTP_GET)
        if not response:
            logger.warn("{0}: Psu status unavailable as ws request {1}"
                    " failed".format(self.rssencl.LDR_R1_ENCL, url))
            return
        if response.status_code != self.rssencl.ws.HTTP_OK:
            if url.find(self.rssencl.ws.LOOPBACK) == -1:
                logger.error("{0}:: http request {1} to poll psu failed with"
                        " err {2}".format(self.rssencl.LDR_R1_ENCL, url, response.status_code))
            return
        try:
            jresponse = json.loads(response.text)
        except ValueError as badjson:
            logger.error("%s returned mal-formed json:\n%s" % (url, badjson))
        if jresponse:
            api_resp = self.rssencl.get_api_status(jresponse['status'])
            if ((api_resp == -1) and
                    (response.status_code == self.rssencl.ws.HTTP_OK)):
                logger.warn("/show/enclosure api response unavailable, "
                        "marking success as http code is 200")
                api_resp = 0
            if api_resp == 0:
                encl_drawers = jresponse["enclosures"][0]["drawers"]
                if encl_drawers:
                    for drawer in encl_drawers:
                        sideplane_list = drawer["sideplanes"]
                        for sideplane in sideplane_list:
                            sideplane_expanders.append(sideplane)
                if sideplane_name == "*":
                    return sideplane_expanders
                else:
                    for expander in sideplane_expanders:
                        if sideplane_name == expander["name"]:
                            return expander
                    else:
                        raise Exception("Resource not Found")
        raise Exception("Resource not Found")

    def _handle_ports_request(self, enclosure_request, resource):
        response = dict()
        logger.info('handling ports request..')
        self._enclosure_type = enclosure_request.split(":")[2]
        self._enclosure_resource_type = enclosure_request.split(":")[3]
        self._resource_id = resource
        if self._enclosure_type.lower() in list(map(lambda enclr_item: enclr_item.value.lower(), ResourceTypes)):
            self._build_generic_info(response)
            # fetch specific info
            # self._build_enclosure_info(response, self._enclosure_type, self._resource_id)
            self._build_sas_port_status_info(response)
        else:
            logger.error("Error: Unsupported enclosure type {}".format(self._sensor_type))
        return response

    def _build_generic_info(self, response):
        """
        Build json with generic information
        :param response:
        :return:
        """
        epoch_time = str(int(time.time()))
        response['instance_id'] = self._resource_id
        response['alert_type'] = AlertTypes.GET.value
        response['severity'] = SeverityTypes.INFORMATIONAL.value
        response['alert_id'] = mon_utils.get_alert_id(epoch_time)
        response['info'] = {
            "site_id": self.rssencl.site_id,
            "rack_id": self.rssencl.rack_id,
            "node_id": self.rssencl.node_id,
            "cluster_id": self.rssencl.cluster_id,
            "resource_type": f"enclosure:{self._enclosure_type.lower()}:{self._enclosure_resource_type.lower()}",
            "resource_id": self._resource_id,
            "event_time": epoch_time,
        }
        # fetch host details
        response["host_id"] = socket.getfqdn()

    def _build_sas_port_status_info(self, response):
        """Retrieve enclosure sas ports status i.e sas link health and phy stats"""

        # make ws request
        sas_url = self.rssencl.build_url(self.rssencl.URI_CLIAPI_SASHEALTHSTATUS)
        self._get_enclosure_data(sas_url, response)

    def _get_enclosure_data(self, sasurl, response):
        logger.info("url comes into _get_enclosure_data is:{0}".format(sasurl))
        sas_response = self.rssencl.ws_request(sasurl, self.rssencl.ws.HTTP_GET)
        logger.info("_get_sas_port_status, sasresponse for coming is:{0}".format(sas_response))

        if not sas_response:
            logger.warn(
                "{0}:: sas port status unavailable for request:{1} --gets failed".format(self.rssencl.LDR_R1_ENCL, url))
            return None

        if sas_response.status_code != self.rssencl.ws.HTTP_OK:
            if sasurl.find(self.rssencl.ws.LOOPBACK) == -1:
                logger.error("{0}:: http request {1} to sas port health status failed with error:{2}".format(
                    self.rssencl.LDR_R1_ENCL, sasurl, sasresponse.status_code))
            return None

        json_response = None
        try:
            json_response = json.loads(sas_response.content)
        except ValueError as v_error:
            logger.error("{0} returned invalid json:\n{1}".format(sasurl, v_error))

        if json_response is not None:
            api_status = self.rssencl.get_api_status(json_response['status'])
            if ((api_status == -1) and (sas_response.status_code == self.rssencl.ws.HTTP_OK)):
                logger.warn("/show/sas-link-health api response unavailable, "
                            "marking success as http code is 200")

            if api_status == 0:
                if self._resource_id == self.RESOURCE_ALL:
                    response['specific_info'] = []
                    response['specific_info'].extend(json_response.get("expander-ports"))
                    for interfc in response['specific_info']:
                        interfc['resource_id'] = interfc['name']
                else:
                    response['specific_info'] = {}
                    for port_enclr in json_response.get("expander-ports"):
                        logger.info(port_enclr)
                        if self._resource_id.lower() == port_enclr['name'].lower():
                            response['specific_info'] = port_enclr
                            break
                    else:
                        response['specific_info']["reason"] = "Data not available for port interface: {}.".format(
                            self._resource_id.lower())

    def _get_system_info(self):
        """ return data from /show/system and /show/version/detail api"""
        system_data = self._get_encl_response(
               self.rssencl.URI_CLIAPI_SHOWSYSTEM,
               self.rssencl.ws.HTTP_GET
        )
        version_data = self._get_encl_response(
            self.rssencl.URI_CLIAPI_SHOWVERSION,
            self.rssencl.ws.HTTP_GET
        )
        error_data = {"error": "failed to get data from enclosure"}
        if system_data:
            try:
                system_data = system_data["system"][0]
                try:
                    del system_data["unhealthy-component"]
                except KeyError:
                    pass
            except (KeyError, IndexError):
                system_data = error_data
        else:
            system_data = error_data

        if version_data:
            try:
                version_data = version_data["versions"]
            except KeyError:
                version_data = error_data
        else:
            version_data = error_data

        response = {
            "system": system_data,
            "versions": version_data
        }
        return response

    def _get_encl_response(self, uri, request_type):
        """ query enclosure and return json data"""
        url = self.rssencl.build_url(uri)
        response = self.rssencl.ws_request(url, request_type)
        if not response:
            logger.warn(f"Failed to get data for {uri}")
            return None
        if response.status_code != self.rssencl.ws.HTTP_OK:
            logger.error(f"Failed to get data for {uri}")
            return None
        try:
            response = json.loads(response.content)
            api_response = self.rssencl.get_api_status(response.get('status'))
            if api_response == 0 or \
                (api_response == -1 and response.status_code == self.rssencl.ws.HTTP_OK):
                return response
            else:
                logger.error(f"invalid data for {uri}")
                return None
        except ValueError as err:
            logger.error(f"invalid data for {uri} {err}")
            return None
