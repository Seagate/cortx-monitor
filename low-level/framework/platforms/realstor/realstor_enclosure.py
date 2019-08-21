"""
 ****************************************************************************
 Filename:          realstor_enclosure.py
 Description:       Common set of Realstor enclosure management apis and utilities
 Creation Date:     07/03/2019
 Author:            Chetan S. Deshmukh

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
import threading
import json
import hashlib
import time

from framework.target.enclosure import StorageEnclosure
from framework.utils.service_logging import logger
from framework.utils.config_reader import ConfigReader
from framework.utils.webservices import WebServices
from framework.utils.jsondata import JsonData

class RealStorEnclosure(StorageEnclosure):
    """RealStor Enclosure Monitor functions using CLI API Webservice Interface"""

    REALSTOR_MC_BOOTWAIT = 0
    DEFAULT_MC_IP = "127.0.0.1"
    WEBSERVICE_TIMEOUT = 20
    MAX_RETRIES = 1

    CONF_SECTION_MC = "STORAGE_ENCLOSURE"
    CONF_REALSTORDISKSENSOR = "REALSTORDISKSENSOR"
    CONF_REALSTORSENSORS = "REALSTORSENSORS"
    DEFAULT_POLL = 30

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

    # Realstor generic health states
    HEALTH_OK = "ok"
    HEALTH_FAULT = "fault"
    HEALTH_DEGRADED = "degraded"

    STATUS_NOTINSTALLED = "not installed"

    DATA_FORMAT_JSON = 'json'

    # Current support for 'cliapi', future scope for 'rest', 'redfish' apis
    # once available
    realstor_supported_interfaces = ['cliapi']

    poll_system_ts = 0

    # resource inmemory cache
    latest_faults = {}

    # check fault irrespective, since memcache faults are mosty copy of latest
    # faults, so no comparison to check for new faults is feasible
    existing_faults = False

    def __init__(self):
        super(RealStorEnclosure, self).__init__()

        # WS Request common headers
        self.ws = WebServices()
        self.common_reqheaders = {}

        self.jsondata = JsonData()
        self.encl_conf = self.CONF_SECTION_MC

        self.system_persistent_cache = self.encl_cache + "system/"
        self.faults_persistent_cache = self.system_persistent_cache + "faults.json"

        # Read in mc value from configuration file
        self.mc1 = self.conf_reader._get_value_with_default(
            self.encl_conf, "primary_controller_ip", self.DEFAULT_MC_IP)
        self.mc1_wsport = self.conf_reader._get_value_with_default(
            self.encl_conf, "primary_controller_port", '')
        self.mc2 = self.conf_reader._get_value_with_default(
            self.encl_conf, "secondary_controller_ip", self.DEFAULT_MC_IP)
        self.mc2_wsport = self.conf_reader._get_value_with_default(
            self.encl_conf, "secondary_controller_port", '')

        self.active_ip = self.mc1
        self.active_wsport = self.mc1_wsport

        self.user = self.conf_reader._get_value_with_default(
            self.encl_conf, "user", self.DEFAULT_USER)
        self.passwd = self.conf_reader._get_value_with_default(
            self.encl_conf, "password", self.DEFAULT_PASSWD)

        self.mc_interface = self.conf_reader._get_value_with_default(
                                self.encl_conf, "mgmt_interface", "cliapi")

        self.pollfreq = int(self.conf_reader._get_value_with_default(
            self.CONF_REALSTORSENSORS, "polling_frequency", self.DEFAULT_POLL))

        if self.mc_interface not in self.realstor_supported_interfaces:
            logger.error("Unspported Realstor interface configured,"
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
                logger.error("makedirs failed with OS error {0}".format(oserr))
        except Exception as err:
            logger.error("makedirs failed with unknown error {0}".format(err))

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
           logger.warn("Non-numeric webservice port configured [%s], ignoring",\
               self.active_wsport)

        url = "http://" + self.active_ip + wsport + "/api" + uri

        return url

    def switch_to_alt_mc(self):
        """Switches active ip between primary and secondary management controller
           ips"""

        if self.active_ip == self.mc1:
            self.active_ip = self.mc2
            self.active_wsport = self.mc2_wsport
        elif self.active_ip == self.mc2:
            self.active_ip = self.mc1
            self.active_wsport = self.mc1_wsport

        logger.debug("Current MC active ip {0}, active wsport {1}\
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

            if not response:
                continue

            if response.status_code != self.ws.HTTP_OK:
                logger.error("%s failed with http code %d" % (url, response.status_code))

                # if call fails with invalid session key request or http 403
                # forbidden request, login & retry
                if response.status_code == self.ws.HTTP_FORBIDDEN and relogin == False:
                    logger.info("%s failed, retrying after login " % (url))

                    self.login()
                    relogin = True
                    continue

                if response.status_code == self.ws.HTTP_TIMEOUT and tried_alt_ip == False:
                    self.switch_to_alt_mc()
                    tried_alt_ip = True
                    continue
            break

        return response

    def check_prcache(self, cachedir):
        """Check for persistent cache dir and create if absent"""
        available = os.path.exists(cachedir)

        if not available:
            logger.info("Missing RAS persistent cache, creating {0}\
                ".format(cachedir))

            try:
                os.makedirs(cachedir)
            except OSError as exc:
                if exc.errno == errno.EEXIST and os.path.isdir(path):
                    pass
                elif os_error.errno == errno.EACCES:
                    logger.critical(
                        "Permission denied while creating dir: {0}".format(path))
            except Exception as err:
                    logger.warn("{0} creation failed with error {1}, alerts"
                    " may get missed on sspl restart or failover!!".format(
                    cachedir,err))

    def login(self):
        """Perform realstor login to get session key & make it available
           in common request headers"""

        cli_api_auth = self.user + '_' + self.passwd

        url = self.build_url(self.URI_CLIAPI_LOGIN)
        auth_hash = hashlib.sha256(cli_api_auth).hexdigest()
        headers = {'datatype':'json'}

        response = self.ws.ws_get(url + auth_hash, headers, \
                       self.WEBSERVICE_TIMEOUT)

        if not response:
            logger.warn("Login webservice request failed {0}".format(url))
            return

        if response.status_code != self.ws.HTTP_OK:
            logger.error("http request for login failed with err %d"
                % response.status_code)
            return

        try:
            jresponse = json.loads(response.content)
        except ValueError as badjson:
            logger.error("%s returned mal-formed json:\n%s" % (url, badjson))

        if jresponse:
            if jresponse['status'][0]['return-code'] == 1:
                sessionKey = jresponse['status'][0]['response']
                self._add_request_headers(sessionKey)
            else:
                logger.error("realstor cli api login FAILED with api err %d" %
                    jresponse['status'][0]['return-code'])

    def check_system_faults_changed(self):
        """Check change in faults state"""

        changed = False

        if self.existing_faults:
            #logger.debug("existing_faults TRUE")
            return True

        if 0 != cmp(self.latest_faults,
            self.memcache_faults):
            changed = True
            logger.warn("System faults state changed, updating cached faults!!")
            self.memcache_faults = self.latest_faults

            #Update faults in persistent cache
            logger.info("Updating faults persistent cache!!")
            self.jsondata.dump(self.memcache_faults,
                self.faults_persistent_cache)

        return changed

    def check_new_fault(self, fault):
        """Check if supplied is new fault"""

        if self.existing_faults:
            #logger.debug("existing_faults TRUE")
            return True

        newkid = False

        if self.memcache_faults and fault:
            for cached in self.memcache_faults:

                if fault["component-id"] == cached["component-id"]:
                    logger.debug("Found cached faulty resource {0}\
                        ".format(fault["component-id"]))

                    if fault["health"] != cached["health"] \
                        or fault["health-reason"] != cached["health-reason"]:
                        logger.debug("New system Fault detected !!!")
                        logger.debug("Health changed for faulty resource {0}\
                            ".format(fault["component-id"]))
                        newkid = True

        return newkid

    def get_api_status(self, jresp):
        """Retreive realstor common api response for cli apis"""

        api_status = -1
        for status in jresp:
            if status["response-type"] != "Info":
                api_status = status["response-type-numeric"]
                break

        return api_status

    def get_system_status(self):
        """Retreive realstor system state info using cli api /show/system"""

        # poll system would get invoked through multiple realstor sensors
        # with less frequency compared to configured polling frequency
        # adding check to comply with polling frequency
        elapsed = time.time() - self.poll_system_ts

        if elapsed < self.pollfreq:
            logger.warn("/show/system request came in {0} seconds,"
                "while configured polling frequency is {1} seconds,"
                "ignoring".format(elapsed, self.pollfreq))
            return

        self.check_prcache(self.system_persistent_cache)
        system = None

        # make ws request
        url = self.build_url(self.URI_CLIAPI_SHOWSYSTEM)
        #logger.info("show system url: %s" % url)

        response = self.ws_request(url, self.ws.HTTP_GET)

        if not response:
            logger.warn("System status unavailable as ws request failed")
            return

        if response.status_code != self.ws.HTTP_OK:
            logger.error("http request to poll system failed with http err %d"
                % response.status_code)
            return

        self.poll_system_ts = time.time()

        try:
            jresponse = json.loads(response.content)
        except ValueError as badjson:
            logger.error("%s returned mal-formed json:\n%s" % (url, badjson))

        if jresponse:
            api_resp = self.get_api_status(jresponse['status'])

            if ((api_resp == -1) and
                   (response.status_code == self.ws.HTTP_OK)):
                logger.warn("/show/system api response unavailable, "
                    "marking success as http code is 200")
                api_resp = 0

            if api_resp == 0:
                system = jresponse['system'][0]
                self.memcache_system = system

            if system:
                # Extract system faults
                self.latest_faults = system["unhealthy-component"]

                #If no in-memory fault cache built yet!
                if not self.memcache_faults:
                    # build from persistent cache if available
                    logger.info(
                        "No cached faults, building from  persistent cache {0}"\
                        .format(self.faults_persistent_cache))

                    self.memcache_faults = self.jsondata.load(
                                               self.faults_persistent_cache)

                    # still if none, build from latest faults & persist
                    if not self.memcache_faults:
                        logger.info("No persistent faults cache, building "
                            "cache from latest faults")

                        self.memcache_faults = self.latest_faults

                        # On SSPL boot, run through existing faults as no cache to
                        # verify with for new faults
                        self.existing_faults = True

                        #logger.debug("existing_faults {0}".\
                        #    format(self.existing_faults))

                        self.jsondata.dump(self.memcache_faults,
                            self.faults_persistent_cache)
                else:
                     # Reset flag as existing faults processed by now
                     # and cached faults are built already
                     self.existing_faults = False
            else:
                logger.error("poll system failed with err %d" % api_resp)

# Object to use as singleton instance
singleton_realstorencl = RealStorEnclosure()
