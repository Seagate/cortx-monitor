"""
 ****************************************************************************
 Filename:          RealStor.py
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

    RESOURCE_DISK_ALL = "*"

    @staticmethod
    def name():
        """ @return: name of the module."""
        return RealStorActuator.ACTUATOR_NAME

    def __init__(self):
        super(RealStorActuator, self).__init__()

        self.rssencl = singleton_realstorencl

        self.request_fru_func = {
            self.REQUEST_GET: {
                self.FRU_DISK: self._get_disk
            }
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

        response = {
          "alert_type":"GET",
          "severity":"informational",
          "host_id": host_id,
          "info": {
            "site_id": self.rssencl.site_id,
            "rack_id": self.rssencl.rack_id,
            "node_id": self.rssencl.node_id,
            "cluster_id": self.rssencl.cluster_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "event_time": epoch_time,
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
        if(disk != self.RESOURCE_DISK_ALL):
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


