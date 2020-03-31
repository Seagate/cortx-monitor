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

import errno
import json
import hashlib
import time

from framework.target.enclosure import StorageEnclosure
from framework.utils.service_logging import logger
from framework.utils.webservices import WebServices
from framework.utils.store_factory import store
from framework.utils import encryptor

class RealStorEnclosure(StorageEnclosure):
    """RealStor Enclosure Monitor functions using CLI API Webservice Interface"""

    REALSTOR_MC_BOOTWAIT = 0
    DEFAULT_MC_IP = "127.0.0.1"
    WEBSERVICE_TIMEOUT = 20
    PERSISTENT_DATA_UPDATE_TIMEOUT = 5
    MAX_RETRIES = 1

    CONF_SECTION_MC = "STORAGE_ENCLOSURE"
    SYSTEM_INFORMATION = "SYSTEM_INFORMATION"
    CONF_REALSTORDISKSENSOR = "REALSTORDISKSENSOR"
    CONF_REALSTORCONTROLLERSENSOR = "REALSTORCONTROLLERSENSOR"
    CONF_REALSTORFANSENSOR = "REALSTORFANSENSOR"
    CONF_REALSTORPSUSENSOR = "REALSTORPSUSENSOR"
    CONF_REALSTORLOGICALVOLUMESENSOR = "REALSTORLOGICALVOLUMESENSOR"
    CONF_REALSTORSIDEPLANEEXPANDERSENSOR = "REALSTORSIDEPLANEEXPANDERSENSOR"
    CONF_REALSTORENCLOSURESENSOR = "REALSTORENCLOSURESENSOR"
    CONF_REALSTORSENSORS = "REALSTORSENSORS"
    DEFAULT_POLL = 30
    SITE_ID = "site_id"
    CLUSTER_ID = "cluster_id"
    NODE_ID = "node_id"
    RACK_ID = "rack_id"

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
    URI_CLIAPI_SHOWEVENTS = "/show/events"

    # Realstor generic health states
    HEALTH_OK = "ok"
    HEALTH_FAULT = "fault"
    HEALTH_DEGRADED = "degraded"

    STATUS_NOTINSTALLED = "not installed"

    DATA_FORMAT_JSON = "json"
    FAULT_KEY = "unhealthy-component"

    # Current support for 'cliapi', future scope for 'rest', 'redfish' apis
    # once available
    realstor_supported_interfaces = ['cliapi']

    poll_system_ts = 0
    mc_timeout_counter = 0

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

        self.site_id = int(self.conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                self.SITE_ID,
                                                0))
        self.rack_id = int(self.conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                self.RACK_ID,
                                                0))
        self.node_id = int(self.conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                self.NODE_ID,
                                                0))

        self.cluster_id = int(self.conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                self.CLUSTER_ID,
                                                0))
        # Decrypt MC Password
        decryption_key = encryptor.gen_key(str(self.cluster_id), str(self.node_id))
        self.passwd = encryptor.decrypt(decryption_key, self.passwd.encode('ascii'))

        if self.mc_interface not in self.realstor_supported_interfaces:
            logger.error("Unspported Realstor interface configured,"
                " monitoring and alerts generation may hamper")
            return

        # login to mc to get session key, required for querying resources
        # periodically
        self.login()

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

        if self.mc1 == self.mc2 and \
            self.mc1_wsport == self.mc2_wsport:
            return

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

            if response is None:
                continue

            if response.status_code != self.ws.HTTP_OK:

                # if call fails with invalid session key request or http 403
                # forbidden request, login & retry
                if response.status_code == self.ws.HTTP_FORBIDDEN and relogin is False:
                    logger.info("%s failed, retrying after login " % (url))

                    self.login()
                    relogin = True
                    continue

                elif (response.status_code == self.ws.HTTP_TIMEOUT or \
                         response.status_code == self.ws.HTTP_CONN_REFUSED) \
                         and tried_alt_ip is False:
                    self.switch_to_alt_mc()
                    tried_alt_ip = True
                    self.mc_timeout_counter += 1
                    continue
            else:
                self.mc_timeout_counter = 0

            break

        return response

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
            logger.warn("Login webservice request failed {0}".format(url))
            return

        if response.status_code != self.ws.HTTP_OK:
            if response.status_code == self.ws.HTTP_TIMEOUT:
                self.mc_timeout_counter += 1
            logger.error("{0}:: http request for login failed with err {1}"\
                .format(self.EES_ENCL, response.status_code))
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

        if self.latest_faults != self.memcache_faults:
            changed = True
            logger.warn("System faults state changed, updating cached faults!!")

        return changed

    def update_memcache_faults(self):
        self.memcache_faults = self.latest_faults

        #Update faults in persistent cache
        logger.info("Updating faults persistent cache!!")
        store.put(self.memcache_faults,
            self.faults_persistent_cache)

    def check_new_fault(self, fault):
        """Check if supplied is new fault"""

        if self.existing_faults:
            #logger.debug("existing_faults TRUE")
            return True

        newkid = False

        if fault not in self.memcache_faults:
            newkid = True
            for cached in self.memcache_faults:
                if fault["component-id"] == cached["component-id"] \
                    and fault["health"] == cached["health"] \
                    and fault["health-reason"] == cached["health-reason"]:
                    newkid = False
                    break

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

        system = None

        # make ws request
        url = self.build_url(self.URI_CLIAPI_SHOWSYSTEM)
        #logger.info("show system url: %s" % url)

        response = self.ws_request(url, self.ws.HTTP_GET)

        if not response:
            logger.warn("System status unavailable as ws request failed")
            return

        if response.status_code != self.ws.HTTP_OK:
            logger.info("{0}:: http request {1} polling system status failed"
                " with http err {2}".format(self.EES_ENCL, url, \
                response.status_code))
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
                # Check if fault exists
                # TODO: use self.FAULT_KEY in system: system.key() generates
                # list and find item in that.
                if not self.FAULT_KEY in system.keys():
                    logger.info("{0} Healthy, no faults seen".format(self.EES_ENCL))
                    return

                # Extract system faults
                self.latest_faults = system[self.FAULT_KEY]

                #If no in-memory fault cache built yet!
                if not self.memcache_faults:
                    # build from persistent cache if available
                    logger.info(
                        "No cached faults, building from  persistent cache {0}"\
                        .format(self.faults_persistent_cache))

                    self.memcache_faults = store.get(
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

                        store.put(self.memcache_faults,
                            self.faults_persistent_cache)
                else:
                     # Reset flag as existing faults processed by now
                     # and cached faults are built already
                     self.existing_faults = False
            else:
                logger.error("poll system failed with err %d" % api_resp)

# Object to use as singleton instance
singleton_realstorencl = RealStorEnclosure()
