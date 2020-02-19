"""
 ****************************************************************************
 Filename:          realstor_enclosure.py
 Description:       Common set of Realstor enclosure management apis and utilities
 Creation Date:     02/18/2020
 Author:            Satish Darade

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import os
import errno
import json
import hashlib
import time

from common.utils.webservices import WebServices
from common.utils.store_factory import store

class RealStorEnclosure(object):
    """RealStor Enclosure Monitor functions using CLI API Webservice Interface"""

    #MC1_IP = "10.237.66.80"
    MC1_IP = "10.230.162.148"
    MC1_WSPORT = "80"
    DEFAULT_MC_IP = "127.0.0.1"
    DEFAULT_MC_WSPORT = "28200"
    WEBSERVICE_TIMEOUT = 20
    MAX_RETRIES = 1

    EES_ENCL = "Realstor 5U84"
    DATA_FORMAT_JSON = "json"
    FAULT_KEY = "unhealthy-component"

    DEFAULT_USER = "manage"
    DEFAULT_PASSWD = "!manage"

    # CLI APIs
    URI_CLIAPI_LOGIN = "/login/"
    URI_CLIAPI_SHOWDISKS = "/show/disks"
    URI_CLIAPI_SHOWSYSTEM = "/show/system"
    URI_CLIAPI_SHOWPSUS = "/show/power-supplies"
    URI_CLIAPI_SHOWCONTROLLERS = "/show/controllers"
    URI_CLIAPI_SHOWFANMODULES = "/show/fan-modules"
    URI_CLIAPI_SHOWENCLOSURE = "/show/enclosure"
    URI_CLIAPI_SHOWDISKGROUPS = "/show/disk-groups"
    URI_CLIAPI_SHOWVOLUMES = "/show/volumes"
    URI_CLIAPI_SHOWSENSORSTATUS = "/show/sensor-status"
    URI_CLIAPI_SASHEALTHSTATUS = "/show/sas-link-health"

    # Current support for 'cliapi', future scope for 'rest', 'redfish' apis
    # once available
    realstor_supported_interfaces = ['cliapi']

    def __init__(self):
        super(RealStorEnclosure, self).__init__()

        # WS Request common headers
        self.ws = WebServices()
        self.common_reqheaders = {}

        self.vol_ras = "/var/eos/sspl/data/"
        self.encl_cache = self.vol_ras + "encl/"
        self.frus = self.encl_cache + "frus/"

        self.system_persistent_cache = self.encl_cache + "system/"
        self.faults_persistent_cache = self.system_persistent_cache + "faults.json"

        # Read in mc value.
        self.mc1 = self.MC1_IP
        self.mc1_wsport = self.MC1_WSPORT
        self.mc2 = self.DEFAULT_MC_IP
        self.mc2_wsport = self.DEFAULT_MC_WSPORT

        self.active_ip = self.mc1
        self.active_wsport = self.mc1_wsport

        self.user = "manage"
        self.passwd = "!manage"

        self.mc_interface = "cliapi"

        if self.mc_interface not in self.realstor_supported_interfaces:
            print("Unspported Realstor interface configured,"
                " monitoring and alerts generation may hamper")
            return

        # login to mc to get session key, required for querying resources
        # periodically
        self.login()

        try:
            if not os.path.exists(self.frus):
                os.makedirs(self.frus)
        except OSError as oserr:
            if oserr.errno != errno.EEXIST:
                print("makedirs failed with OS error {0}".format(oserr))
        except Exception as err:
            print("makedirs failed with unknown error {0}".format(err))

    def _add_request_headers(self, sessionKey):
        """Add common request headers"""
        self.common_reqheaders['datatype'] = self.DATA_FORMAT_JSON
        self.common_reqheaders['sessionKey'] = sessionKey

    def build_url(self, uri):
        """Build request url"""

        wsport = ""

        if self.active_wsport.isdigit():
           wsport = ":" + self.active_wsport
        else:
           print("Non-numeric webservice port configured [%s], ignoring",\
               self.active_wsport)

        url = "http://" + self.active_ip + wsport + "/api" + uri

        return url

    def switch_to_alt_mc(self):
        """Switches active ip between primary and secondary management controller
           ips"""

        if self.mc1 == self.mc2 and \
            self.mc1_wsport == self.mc2_wsport:
            return

        if self.active_ip == self.mc1:
            self.active_ip = self.mc2
            self.active_wsport = self.mc2_wsport
        elif self.active_ip == self.mc2:
            self.active_ip = self.mc1
            self.active_wsport = self.mc1_wsport

        print("Current MC active ip {0}, active wsport {1}\
            ".format(self.active_ip, self.active_wsport))

    def ws_request(self, url, method, retry_count=MAX_RETRIES,
            post_data=""):
        """Make webservice requests using common utils"""
        response = None
        relogin = False
        tried_alt_ip = False

        while retry_count:
            response = self.ws.ws_request(method, url,
                       self.common_reqheaders, post_data,
                       self.WEBSERVICE_TIMEOUT)

            retry_count -= 1

            if response is None:
                continue

            if response.status_code != self.ws.HTTP_OK:

                # if call fails with invalid session key request or http 403
                # forbidden request, login & retry
                if response.status_code == self.ws.HTTP_FORBIDDEN and relogin is False:
                    print("%s failed, retrying after login " % (url))

                    self.login()
                    relogin = True
                    continue

                elif (response.status_code == self.ws.HTTP_TIMEOUT or \
                         response.status_code == self.ws.HTTP_CONN_REFUSED) \
                         and tried_alt_ip is False:
                    self.switch_to_alt_mc()
                    tried_alt_ip = True
                    continue
            break

        return response

    def check_prcache(self, cachedir):
        """Check for persistent cache dir and create if absent"""
        available = os.path.exists(cachedir)

        if available:
            print("RAS persistent cache already prasent, ignoring {0}\
                ".format(cachedir))
            return False
        else:
            print("Missing RAS persistent cache, creating {0}\
                ".format(cachedir))

            try:
                os.makedirs(cachedir)
                return True
            except OSError as exc:
                if exc.errno == errno.EEXIST and os.path.isdir(path):
                    pass
                elif exc.errno == errno.EACCES:
                    print(
                        "Permission denied while creating dir: {0}".format(path))
            except Exception as err:
                    print("{0} creation failed with error {1}, alerts"
                    " may get missed on sspl restart or failover!!".format(
                    cachedir,err))

    def login(self):
        """Perform realstor login to get session key & make it available
           in common request headers"""

        cli_api_auth = self.user + '_' + self.passwd

        url = self.build_url(self.URI_CLIAPI_LOGIN)
        auth_hash = hashlib.sha256(cli_api_auth.encode('utf-8')).hexdigest()
        headers = {'datatype':'json'}

        response = self.ws.ws_get(url + auth_hash, headers, \
                       self.WEBSERVICE_TIMEOUT)

        if not response:
            print("Login webservice request failed {0}".format(url))
            return

        if response.status_code != self.ws.HTTP_OK:
            print("{0}:: http request for login failed with err {1}"\
                .format(self.EES_ENCL, response.status_code))
            return

        try:
            jresponse = json.loads(response.content)
        except ValueError as badjson:
            print("%s returned mal-formed json:\n%s" % (url, badjson))

        if jresponse:
            if jresponse['status'][0]['return-code'] == 1:
                sessionKey = jresponse['status'][0]['response']
                self._add_request_headers(sessionKey)
            else:
                print("realstor cli api login FAILED with api err %d" %
                    jresponse['status'][0]['return-code'])

    def _get_realstor_show_data(self, fru):
        """Receives fru data from API.
           URL: http://<host>/api/show/<fru>
        """
        if fru == "controllers":
            show_fru = self.URI_CLIAPI_SHOWCONTROLLERS
        elif fru == "fan-modules":
            show_fru = self.URI_CLIAPI_SHOWFANMODULES
        elif fru == "power-supplies":
            show_fru = self.URI_CLIAPI_SHOWPSUS
        elif fru == "drives":
            show_fru = self.URI_CLIAPI_SHOWDISKS
        elif fru == "enclosures":
            show_fru = self.URI_CLIAPI_SHOWENCLOSURE
        elif fru == "disk-groups":
            show_fru = self.URI_CLIAPI_SHOWDISKGROUPS
        elif fru == "volumes":
            show_fru = self.URI_CLIAPI_SHOWVOLUMES
        elif fru == "system":
            show_fru = self.URI_CLIAPI_SHOWSYSTEM
        elif fru == "sensor-status":
            show_fru = self.URI_CLIAPI_SHOWSENSORSTATUS
            fru = "sensors"
        elif fru == "sas-link-health":
            show_fru = self.URI_CLIAPI_SASHEALTHSTATUS
            fru = "expander-ports"

        url = self.build_url(show_fru)

        response = self.ws_request(url, self.ws.HTTP_GET)

        if not response:
            print("{0}:: {2} status unavailable as ws request {1}"
                " failed".format(self.EES_ENCL, url, fru))
            return

        if response.status_code != self.ws.HTTP_OK:
            if url.find(self.ws.LOOPBACK) == -1:
                print("{0}:: http request {1} to get {3} failed with"
                    " err {2}".format(self.EES_ENCL, url, response.status_code, fru))
            return

        response_data = json.loads(response.text)
        fru_data = response_data.get(fru)
        return fru_data

realstor_enclosure = RealStorEnclosure()
