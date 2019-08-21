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
from framework.utils.service_logging import logger

class WebServices(object):
    # Http Methods
    HTTP_GET  = "GET"
    HTTP_POST = "POST"
    HTTP_PUT  = "PUT"
    HTTP_DELETE = "DELETE"

    # HTTP Response codes
    HTTP_OK = 200
    HTTP_BADRQ = 400
    HTTP_FORBIDDEN = 404
    HTTP_TIMEOUT = 503


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

            if not wsresponse:
                wsresponse.raise_for_status()

        except requests.exceptions.ConnectionError as connerr:
                logger.error("Connection Error for ws api {0} - {1}"\
                    .format(url,connerr))
        except requests.exceptions.HTTPError as httperr:
                logger.error("HTTP Error encountered for api {0} - {1}"\
                    .format(url,httperr))
        except requests.exceptions.Timeout as toerr:
                logger.error("Timeout for api {0} - {1}".format(url,toerr))
        except Exception as err:
                logger.error("Unknown error for api {0} - {1}".format(url,err))

        return wsresponse

    def ws_get(self, url, headers, timeout):
        """Webservice GET request"""
        return  self.ws_request(self.HTTP_GET, url, headers, None, timeout)

    def ws_post(self, url, headers, postdata, timeout):
        """Webservice POST request"""
        return self.ws_request(self.HTTP_POST, url, headers, postdata, timeout)
