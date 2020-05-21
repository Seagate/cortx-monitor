"""
 ****************************************************************************
 Filename:          webservices.py
 Description:       Webservice Class to abstract over actual python lib or web
                    framework used to handle generic web services
 Creation Date:     06/11/2019
 Author:            Chetan Deshmukh <chetan.deshmukh@seagate.com>

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2019/06/11 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""


import requests
from requests.exceptions import Timeout, ConnectionError, HTTPError
from framework.utils.service_logging import logger

class WebServices(object):
    # Http Methods
    HTTP_GET  = "GET"
    HTTP_POST = "POST"
    HTTP_PUT  = "PUT"
    HTTP_DELETE = "DELETE"

    # HTTP Response codes
    HTTP_CONN_REFUSED = 111
    HTTP_OK = 200
    HTTP_BADRQ = 400
    HTTP_FORBIDDEN = 403
    HTTP_NOTFOUND = 404
    HTTP_TIMEOUT = 408
    HTTP_NO_ROUTE_TO_HOST = 113
    SERVICE_UNAVIALABLE = 503

    LOOPBACK = "127.0.0.1"

    def __init__(self):
        super(WebServices, self).__init__()

        self.http_methods = [self.HTTP_GET, self.HTTP_POST]

    def ws_request(self, method, url, hdrs, postdata, tout):
        """Make webservice request"""
        wsresponse = None

        try:
            if method == self.HTTP_GET:
                wsresponse = requests.get(url, headers=hdrs, timeout=tout)
            elif method == self.HTTP_POST:
                wsresponse = requests.post(url, headers=hdrs, data=postdata,
                               timeout=tout)

            wsresponse.raise_for_status()

        except (ConnectionError, HTTPError, Timeout, Exception) as err:

            errstr = str(err)

            if not wsresponse:
                wsresponse = requests.Response()

            # Extract error code from exception obj and set in response
            if isinstance(err, ConnectionError):

                if url.find(self.LOOPBACK) == -1:
                    logger.debug("Connection Error for ws api {0} - {1}"\
                        .format(url,err))

                if errstr.find("error:") != -1:
                    wsresponse.status_code = \
                        int(errstr[errstr.find("error(") + 6:].split(",")[0])
                else:
                    wsresponse.status_code = self.HTTP_CONN_REFUSED

            elif isinstance(err, HTTPError):
                # HttpError exception example "403 Client Error: Forbidden"
                if url.find(self.LOOPBACK) == -1:
                    logger.debug("HTTP Error encountered for api {0} - {1}"\
                        .format(url,err))

                if errstr.find("Client Error") != -1:
                    wsresponse.status_code = int(errstr.split(" ")[0])
                else:
                    wsresponse.status_code = self.HTTP_CONN_REFUSED
            elif isinstance(err, Timeout):

                if url.find(self.LOOPBACK) == -1:
                    logger.debug("Timeout for api {0} - {1}".format(url,err))
                    wsresponse.status_code = self.HTTP_TIMEOUT
            else:
                # Default to an error code
                wsresponse.status_code = self.SERVICE_UNAVIALABLE

                if url.find(self.LOOPBACK) == -1:
                    logger.debug("Error encountered for api {0} - {1}"\
                        ", defaulting to err {2}"\
                        .format(url,err,wsresponse.status_code))

        return wsresponse

    def ws_get(self, url, headers, timeout):
        """Webservice GET request"""
        return  self.ws_request(self.HTTP_GET, url, headers, None, timeout)

    def ws_post(self, url, headers, postdata, timeout):
        """Webservice POST request"""
        return self.ws_request(self.HTTP_POST, url, headers, postdata, timeout)
