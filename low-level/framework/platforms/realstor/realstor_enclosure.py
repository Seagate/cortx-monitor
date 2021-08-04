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
  Description:       Common set of Realstor enclosure management apis and utilities
 ****************************************************************************
"""

import errno
import hashlib
import json
import time

from framework.base.sspl_constants import ServiceTypes
from framework.target.enclosure import StorageEnclosure
from framework.utils import encryptor
from framework.utils.conf_utils import (GLOBAL_CONF, MGMT_INTERFACE,
                                        POLLING_FREQUENCY, SSPL_CONF,
                                        STORAGE_ENCLOSURE, Conf,
                                        CNTRLR_PRIMARY_IP_KEY, CNTRLR_PRIMARY_PORT_KEY,
                                        CNTRLR_SECONDARY_IP_KEY, CNTRLR_SECONDARY_PORT_KEY,
                                        ENCLOSURE, CNTRLR_USER_KEY, CNTRLR_SECRET_KEY)
from framework.utils.service_logging import logger
from framework.utils.store_factory import store
from framework.utils.webservices import WebServices


class RealStorEnclosure(StorageEnclosure):
    """RealStor Enclosure Monitor functions using CLI API Webservice Interface"""

    REALSTOR_MC_BOOTWAIT = 0
    DEFAULT_MC_IP = "127.0.0.1"
    WEBSERVICE_TIMEOUT = 20
    PERSISTENT_DATA_UPDATE_TIMEOUT = 5
    MAX_RETRIES = 2

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
    URI_CLIAPI_NETWORKHEALTHSTATUS = "/show/network"
    URI_CLIAPI_SHOWEVENTS = "/show/events"
    URI_CLIAPI_SHOWVERSION = "/show/version/detail"
    URI_CLIAPI_SHOWFRUS = "/show/frus"
    URI_CLIAPI_BASE = "/"
    URI_CLIAPI_DOWNLOADDEBUGDATA = "/downloadDebugData"
    URL_ENCLLOGS_POSTDATA = "/api/collectDebugData"

    # CLI APIs Response status strings
    CLIAPI_RESP_INVSESSION = "Invalid sessionkey"
    CLIAPI_RESP_FAILURE = 2

    # Realstor generic health states
    HEALTH_OK = "ok"
    HEALTH_FAULT = "fault"
    HEALTH_DEGRADED = "degraded"

    STATUS_NOTINSTALLED = "not installed"

    DATA_FORMAT_JSON = "json"
    FAULT_KEY = "unhealthy-component"

    # Realstor FRUs mapping
    fru_mapping = {
        "fan": "FAN MODULE",
        "psu": "POWER_SUPPLY",
        "sideplane": "SIDEPLANE"
    }

    # Current support for 'cliapi', future scope for 'rest', 'redfish' apis
    # once available
    realstor_supported_interfaces = ['cliapi']

    poll_system_ts = 0
    mc_timeout_counter = 0
    # ws_response_status: HTTP response status code. eg: 200 for HTTP_OK
    # used in realstor_enclosure_sensor to decide on FAULT_RESOLVED condition.
    ws_response_status = None

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
        self.mc1 = Conf.get(GLOBAL_CONF, CNTRLR_PRIMARY_IP_KEY, self.DEFAULT_MC_IP)
        self.mc1_wsport = str(Conf.get(GLOBAL_CONF, CNTRLR_PRIMARY_PORT_KEY, ''))
        self.mc2 = Conf.get(GLOBAL_CONF, CNTRLR_SECONDARY_IP_KEY, self.DEFAULT_MC_IP)
        self.mc2_wsport = str(Conf.get(GLOBAL_CONF, CNTRLR_SECONDARY_PORT_KEY, ''))

        self.active_ip = self.mc1
        self.active_wsport = self.mc1_wsport

        self.user = Conf.get(GLOBAL_CONF, CNTRLR_USER_KEY, self.DEFAULT_USER)
        _secret = Conf.get(GLOBAL_CONF, CNTRLR_SECRET_KEY, self.DEFAULT_PASSWD)

        self.mc_interface = Conf.get(SSPL_CONF, f"{STORAGE_ENCLOSURE}>{MGMT_INTERFACE}", "cliapi")

        self.pollfreq = int(Conf.get(SSPL_CONF, f"{self.CONF_REALSTORSENSORS}>{POLLING_FREQUENCY}",
                        self.DEFAULT_POLL))

        # Decrypt MC secret
        decryption_key = encryptor.gen_key(ENCLOSURE,
            ServiceTypes.STORAGE_ENCLOSURE.value)
        self.__passwd = encryptor.decrypt(decryption_key, _secret, "RealStoreEncl")

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

        self.login()
        logger.debug("Current MC active ip {0}, active wsport {1}. Logged-in\
            ".format(self.active_ip, self.active_wsport))

    def ws_request(self, url, method, retry_count=MAX_RETRIES,
            post_data=""):
        """Make webservice requests using common utils"""
        response = None
        retried_login = False
        need_relogin = False
        tried_alt_ip = False

        while retry_count:
            if tried_alt_ip:
                # Extract show fru name from old URL to update alternative IP.
                url = self.build_url(url[url.index('/api/'):].replace('/api',''))

            response = self.ws.ws_request(method, url,
                       self.common_reqheaders, post_data,
                       self.WEBSERVICE_TIMEOUT)

            retry_count -= 1

            if response is None:
                continue

            self.ws_response_status = response.status_code

            if response.status_code == self.ws.HTTP_OK:

                self.mc_timeout_counter = 0

                try:
                    jresponse = json.loads(response.content)

                    #TODO: Need a way to check return-code 2 in more optimal way if possible,
                    # currently being checked for all http 200 responses
                    if jresponse:

                        if jresponse['status'][0]['return-code'] == self.CLIAPI_RESP_FAILURE:
                            response_status = jresponse['status'][0]['response']

                            # if call fails with invalid session key request
                            # seen in G280 fw version
                            if self.CLIAPI_RESP_INVSESSION in response_status:
                               need_relogin = True

                except ValueError as badjson:
                    logger.error("%s returned mal-formed json:\n%s" % (url, badjson))

            # http 403 forbidden request, login & retry
            elif (response.status_code == self.ws.HTTP_FORBIDDEN or \
                need_relogin) and retried_login is False:
                logger.info("%s failed, retrying after login " % (url))

                self.login()
                retried_login = True
                need_relogin = False
                continue

            elif (response.status_code == self.ws.HTTP_TIMEOUT or \
                     response.status_code == self.ws.HTTP_CONN_REFUSED or \
                     response.status_code == self.ws.HTTP_NO_ROUTE_TO_HOST) \
                     and tried_alt_ip is False:
                self.switch_to_alt_mc()
                tried_alt_ip = True
                self.mc_timeout_counter += 1
                continue

            break

        return response

    def login(self):
        """Perform realstor login to get session key & make it available
           in common request headers"""

        cli_api_auth = self.user + '_' + self.__passwd

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
                .format(self.LDR_R1_ENCL, response.status_code))
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
                " with http err {2}".format(self.LDR_R1_ENCL, url, \
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
                    logger.debug("{0} Healthy, no faults seen".format(self.LDR_R1_ENCL))
                    self.latest_faults = {}
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

    def get_realstor_encl_data(self, fru: str):
        """Fetch fru information through webservice API."""
        fru_data = []
        fru_uri_map = {
            "controllers": self.URI_CLIAPI_SHOWCONTROLLERS,
            "power-supplies": self.URI_CLIAPI_SHOWPSUS,
            "sensors": self.URI_CLIAPI_SHOWSENSORSTATUS,
            "volumes": self.URI_CLIAPI_SHOWVOLUMES,
            "disk-groups": self.URI_CLIAPI_SHOWDISKGROUPS,
            "enclosures": self.URI_CLIAPI_SHOWENCLOSURE,
            "network-parameters": self.URI_CLIAPI_NETWORKHEALTHSTATUS,
            "drives": self.URI_CLIAPI_SHOWDISKS,
            "expander-ports": self.URI_CLIAPI_SASHEALTHSTATUS,
            "fan-modules": self.URI_CLIAPI_SHOWFANMODULES,
            "frus": self.URI_CLIAPI_SHOWFRUS,
            "versions": self.URI_CLIAPI_SHOWVERSION
        }
        url = self.build_url(fru_uri_map.get(fru))
        response = self.ws_request(url, self.ws.HTTP_GET)
        if fru == "frus":
            fru = "enclosure-fru"

        if not response or response.status_code != self.ws.HTTP_OK:
            return []
        elif response or response.status_code == self.ws.HTTP_OK:
            response_data = json.loads(response.text)
            fru_data = response_data.get(fru)

        return fru_data

    def load_storage_fru_list(self):
        """Get Storage FRU list and merge it with storage_fru_list,
        maintained in global config, with which FRU list can be extended
        for a solution.

        Ex: Storage Enclosures not listing disk as FRU,
        though its most common FRU in storage, and
        practically it can be replaced easily.
        So if for a solution, FRU list needs to be extended
        beyond what publishes, 'storage_fru_list' from global config
        can be used.
        Some of the usual FRU examples are:- disk.

        """
        self.fru_list = []
        # Read FRU data using /show/frus cli api.
        fru_data = singleton_realstorencl.get_realstor_encl_data("frus")
        for fru_dict in fru_data:
            if "name" in fru_dict.keys():
                self.fru_list.append(fru_dict["name"])
        self.fru_list = list(set(self.fru_list))
        try:
            self.hot_swapped_frus = Conf.get(GLOBAL_CONF,
                "storage_enclosure>storage_fru_list>hot_swappable",
                ['disk', 'controller'])
            self.cold_swapped_frus = Conf.get(GLOBAL_CONF,
                "storage_enclosure>storage_fru_list",
                [])
        except ValueError as e:
            logger.error("Failed to get storage_fru_list from config."
                         f"Error:{e}")
        self.fru_list = list(set(self.fru_list + self.hot_swapped_frus +
                                 self.cold_swapped_frus))
        logger.info(f"Fetched Enclosure FRU list:{self.fru_list}")

    def is_storage_fru(self, fru):
        try:
            is_fru = True if fru in self.fru_list or \
                self.fru_mapping[fru] in self.fru_list else False
        except KeyError:
            is_fru = False

        fru_str = str(is_fru).lower()
        if is_fru:
            if fru in self.hot_swapped_frus:
                fru_str = str(is_fru).lower() + ":" + "hot_swappable"
            elif fru in self.cold_swapped_frus:
                fru_str = str(is_fru).lower() + ":" + "cold_swappable"
            else:
                fru_str = str(is_fru).lower() + ":" + "unknown"
        return fru_str


# Object to use as singleton instance
singleton_realstorencl = RealStorEnclosure()
