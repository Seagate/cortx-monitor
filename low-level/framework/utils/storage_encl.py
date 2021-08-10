#!/usr/bin/env python3

# CORTX Python common library.
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

import time
import json

from framework.base import sspl_constants as sspl_const
from framework.platforms.realstor.realstor_enclosure \
    import singleton_realstorencl


class StorageEncl:
    """Base class for storage enclosure related utility functions."""

    def get_enclosure_logs(self, file_name, logger):
        """Accumulate enclosure logs & write to supplied file"""
        url = singleton_realstorencl.build_url(
            singleton_realstorencl.URI_CLIAPI_BASE)
        COLLECTING_DEBUG_LOG_STARTED = False
        for encl_trigger_log_retry_index in range(0,
                                sspl_const.ENCL_TRIGGER_LOG_MAX_RETRY):
            post_data_string = '{0}/"{1}"{2}"{3}'.format(
                singleton_realstorencl.URL_ENCLLOGS_POSTDATA,
                sspl_const.SUPPORT_REQUESTOR_NAME,
                sspl_const.SUPPORT_EMAIL_ID,
                sspl_const.SUPPORT_CONTACT_NUMBER)
            response = singleton_realstorencl\
                .ws_request(url,
                            singleton_realstorencl.ws.HTTP_POST,
                            post_data=post_data_string)

            if not response:
                logger.error("{0} status unavailable as ws request {1}"
                             " failed".format(
                                 singleton_realstorencl.LDR_R1_ENCL,
                                 url))
                break

            elif response.status_code != singleton_realstorencl.ws.HTTP_OK:
                logger.error("{0} http request {1} to get {3} failed "
                             "with err {2} enclosure trigger log retry "
                             "index {4}".format(
                                 singleton_realstorencl.LDR_R1_ENCL,
                                 url,
                                 response.status_code,
                                 "Debug log",
                                 encl_trigger_log_retry_index))

            else:
                response_data = response.json()
                if response_data["status"][0]["response-type"] == "Success" \
                        and response_data["status"][0]["response"] == "Collecting debug logs.":
                    logger.info("Collecting enclosure debug logs in progress")
                    COLLECTING_DEBUG_LOG_STARTED = True
                    break
                else:
                    logger.error("{0}:: http request {1} to get {3} failed with "
                                 "response-type {2}".format(
                                     singleton_realstorencl.LDR_R1_ENCL,
                                     url,
                                     response_data["status"][0]["response-type"],
                                     "Debug log"))

        if COLLECTING_DEBUG_LOG_STARTED is True:
            self.enclosure_wwn = self.get_enclosure_wwn(singleton_realstorencl, logger)
            url = singleton_realstorencl.build_url(
                singleton_realstorencl.URI_CLIAPI_DOWNLOADDEBUGDATA)
            for encl_download_retry_index in range(0,
                                                   sspl_const.ENCL_DOWNLOAD_LOG_MAX_RETRY):
                response = singleton_realstorencl.ws_request(
                    url, singleton_realstorencl.ws.HTTP_GET)
                if not response:
                    logger.error("{0}:: {2} status unavailable as ws request {1}"
                                 " failed".format(
                                     singleton_realstorencl.LDR_R1_ENCL,
                                     url,
                                     "Debug log"))
                elif response.status_code != singleton_realstorencl.ws.HTTP_OK:
                    logger.error("{0}:: http request {1} to get {3} failed "
                                 "with error {2}".format(
                                     singleton_realstorencl.LDR_R1_ENCL,
                                     url,
                                     response.status_code,
                                     "Debug log"))
                else:
                    if response.headers.get('Content-Type') == 'application/json; charset="utf-8"':
                        response_data = response.json()
                        if response_data["status"][0]["response-type"] == "Error":
                            time.sleep(
                                sspl_const.ENCL_DOWNLOAD_LOG_WAIT_BEFORE_RETRY)
                        else:
                            logger.error("ERR: Unexpected response-type {0} URL {1}".format(
                                response_data["status"][0]["response-type"], url))
                            break
                    elif response.headers.get('Content-Type') == 'IntentionallyUnknownMimeType; charset="utf-8"':
                        if response.headers.get('content-disposition') == 'attachment; filename="store.zip"':
                            with open(file_name, 'wb') as enclosure_resp:
                                enclosure_resp.write(response.content)
                                enclosure_resp.close()
                                logger.info(
                                    "Enclosure debug logs saved successfully")
                        else:
                            logger.error(
                                "ERR: No attachment found::{0}".format(url))
                        break
                    else:
                        logger.error(
                            "ERR: Unknown Content-Type::{0}".format(url))
                        break
                if encl_download_retry_index == (sspl_const.ENCL_DOWNLOAD_LOG_MAX_RETRY - 1):
                    logger.error(
                        "ERR: Enclosure debug logs retry count exceeded::{0}".format(url))

    def get_enclosure_wwn(self, singleton_realstorencl, logger):
        url = singleton_realstorencl.build_url(
            singleton_realstorencl.URI_CLIAPI_SHOWENCLOSURE)
        response = singleton_realstorencl.ws_request(
            url, singleton_realstorencl.ws.HTTP_GET)

        if not response:
            logger.error("{0}:: {2} status unavailable as ws request {1}"
                         " failed".format(singleton_realstorencl.EES_ENCL, url, fru))
            return

        if response.status_code != singleton_realstorencl.ws.HTTP_OK:
            if url.find(singleton_realstorencl.ws.LOOPBACK) == -1:
                logger.error("{0}:: http request {1} to get {3} failed with"
                             " err {2}".format(singleton_realstorencl.EES_ENCL, url, response.status_code, fru))
            return

        response_data = json.loads(response.text)
        enclosure_wwn = response_data.get("enclosures")[0]["enclosure-wwn"]
        return enclosure_wwn
