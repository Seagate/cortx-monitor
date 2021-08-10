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

import os
import sys
import glob
import time
import json
import errno
import shlex
import shutil
import psutil
import tarfile
import argparse
import subprocess

import logging

from datetime import datetime

from cortx.utils.conf_store import Conf
from cortx.utils import const
from cortx.utils.kv_store import KvStoreFactory
from framework.base import sspl_constants as sspl_const
from framework.utils.conf_utils import (
    Conf, SSPL_CONF, SYSTEM_INFORMATION, SSPL_STATE)
from framework.utils.ipmi_client import IpmiFactory
from cortx.utils.process import SimpleProcess

# Load cortx common config
store_type = "json"
config_url = "%s://%s" % (store_type, const.CORTX_CONF_FILE)
common_config = KvStoreFactory.get_instance(config_url)
common_config.load()

# Load bundle request request status tracker
try:
    os.makedirs(common_config.get(
        ["discovery>resource_map>location"])[0], exist_ok=True)
except PermissionError as err:
    print("Failed to create default store directory. %s" % err)
requests_url = "%s://%s" % (store_type, os.path.join(
    common_config.get(["discovery>resource_map>location"])[0],
    "requests.json"))
req_register = KvStoreFactory.get_instance(requests_url)
req_register.load()


class SupportBundleError(Exception):
    """Generic Exception with error code and output."""

    def __init__(self, rc, message, *args):
        """Initialize with custom error message and return code."""
        self._rc = rc
        self._desc = message % (args)

    def __str__(self):
        """Format error string."""
        if self._rc == 0:
            return self._desc
        return "SupportBundleError(%d): %s" % (self._rc, self._desc)


class BundleRequestHandler:
    """Handles SSPL support bundle requests."""
    INPROGRESS = "In-progress"
    SUCCESS = "Success"
    FAILED = "Failed"

    def get_processing_status(req_id):
        """
        Returns "in-progress" if any request is being processed.
        Otherwise returns "Success" or "Failed (with reason)" status.
        """
        if not req_id:
            raise SupportBundleError(errno.EINVAL, "Invalid request ID.")
        status_list = req_register.get(["%s>status" % req_id])
        status = status_list[0] if status_list else None

        if not status:
            raise SupportBundleError(
                errno.EINVAL, "Request ID '%s' not found." % req_id)
        else:
            # Set failed status to stale request ID
            expiry_sec = int(common_config.get(
                ["discovery>resource_map>expiry_sec"])[0])
            last_reboot = int(psutil.boot_time())
            # Set request is expired if processing time exceeds
            system_time = time.strptime(
                req_register.get(["%s>time" % req_id])[0],
                '%Y-%m-%d %H:%M:%S')
            req_start_time = int(time.mktime(system_time))
            current_time = int(time.time())
            is_req_expired = (current_time - req_start_time) > expiry_sec
            if is_req_expired or (last_reboot > req_start_time and
                                  status is BundleRequestHandler.INPROGRESS):
                # Set request state as failed
                BundleRequestHandler._update_request_status(
                    req_id, "Failed - request is expired.")
            status = req_register.get(["%s>status" % req_id])[0]

        return status

    def _update_request_status(req_id, status):
        """Updates processed request information."""
        req_info = req_register.get(["%s" % req_id])[0]
        req_info.update({
            "status": status,
            "time": datetime.strftime(
                datetime.now(), '%Y-%m-%d %H:%M:%S')
        })
        req_register.set(["%s" % req_id], [req_info])

    @staticmethod
    def _add_bundle_request(req_id, url):
        """Updates new request information."""
        req_info = {
            "status": BundleRequestHandler.INPROGRESS,
            "url": url,
            "time": datetime.strftime(
                datetime.now(), '%Y-%m-%d %H:%M:%S')
        }
        req_register.set(["%s" % req_id], [req_info])


class SupportBundle(object):
    """SSPL support bundle class"""
    _tmp_dir = '/tmp/cortx'
    _default_path = '%s/support_bundle/' % _tmp_dir
    _tar_name = 'sspl'
    _tmp_src = '%s/%s/' % (_tmp_dir, _tar_name)
    _conf_file = 'json:///etc/cortx/cluster.conf'

    def __init__(self):

        self.SYS_INFORMATION = "SYSTEM_INFORMATION"
        self.IEM_SENSOR = "IEMSENSOR"
        self.localTempPath = "/tmp/support_bundle/"
        self.sspl_log_default = f"/var/log/{sspl_const.PRODUCT_FAMILY}/sspl"
        self.iem_log_default = f"/var/log/{sspl_const.PRODUCT_FAMILY}/iem"
        self.sspl_conf_dir = f"{sspl_const.SSPL_SB_TMP}/sspl_conf/"
        self.ipmi_sel_data = f"{sspl_const.SSPL_SB_TMP}/ipmi_sel_data_{str(int(time.time()))}.txt"
        self.boot_drvs_dta = f'{sspl_const.SSPL_SB_TMP}/Server_OS_boot_drives_SMART_data_{str(int(time.time()))}'
        self.enclosure_log = f"{sspl_const.SSPL_SB_TMP}/enclosure_logs.zip"
        self.enclosure_wwn = "NA"
        self.sspl_log_dir = Conf.get(SSPL_CONF, "%s>sspl_log_file_path" %
                                     (self.SYS_INFORMATION)).replace("/sspl.log", "")
        self.iem_log_dir = Conf.get(SSPL_CONF, "%s>log_file_path" %
                                    (self.IEM_SENSOR)).replace("/iem_messages", "")

    def generate(self, args):
        if os.path.exists(SupportBundle._tmp_src):
            SupportBundle.__clear_tmp_files()
        bundle_time = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        self.prepare_bundle(args.bundle_id, args.target_path,
                            bundle_time, args.noencl)

        SupportBundle.__clear_tmp_files()

        time.sleep(2)
        status = SupportBundle().get_status(args.bundle_id)
        print(status)

    @staticmethod
    def get_status(bundle_id: str):
        """Get status of support bundle."""
        status = None
        req_id = "sb_%s" % bundle_id
        sspl_sb_id = req_register.get(["%s>sspl_sb_id" % req_id])
        request_status = BundleRequestHandler.get_processing_status(
            sspl_sb_id[0])
        # Extract sspl sb request status from the message.
        # Example : "Failed - error(22): Invalid request"
        status = request_status.split(" ")[0]
        if status != "In-progress":
            return status
        return None

    def prepare_bundle(self, bundle_id: str, target_path: str, bundle_time: str, include_encl):
        """Collect sspl support bundle data."""
        directory = os.path.dirname(SupportBundle._tmp_src)
        if not os.path.exists(directory):
            os.makedirs(directory)
        tar_name, file_name = SupportBundle.__generate_file_names(
            bundle_id, bundle_time)
        tar_file = os.path.join(target_path, tar_name + '.tar.gz')

        sspl_sb_id = self.get_sspl_bundle_data(target_path, include_encl)

        self._generate_tar(target_path, tar_name)
        SupportBundle._update_bundle_id(bundle_id, sspl_sb_id,
                                         tar_file)

    def get_sspl_bundle_data(self, file_path, include_encl):
        print(include_encl)
        request_id = datetime.strftime(datetime.now(),
                                       '%Y%m%d%H%M%S%f')
        BundleRequestHandler._add_bundle_request(request_id, file_path)

        if file_path:
            if os.path.exists(file_path):
                self.localTempPath = file_path+"sspl/"
            else:
                msg = "Given path %s doesn't exist" % (file_path)
                self.__clear_tmp_files()
                raise SupportBundleError(1, msg)
        os.makedirs(self.localTempPath, exist_ok=True)
        try:
            DEFAULT_STATE = Conf.get(
                SSPL_CONF, f"{SYSTEM_INFORMATION}>{SSPL_STATE}", "active")
            try:
                sspl_state = open(
                    f"/var/{sspl_const.PRODUCT_FAMILY}/sspl/data/state.txt").readline().rstrip().split("=")
                # Capturing enclosure logs only when sspl state is active
                sspl_state = sspl_state[1] if len(
                    sspl_state) == 2 else DEFAULT_STATE
                if not sspl_state == 'active':
                    logger.info("SSPL is in 'degraded' mode,"
                                "so enclosure data not collected as part of this node support bundle.")

            except (FileNotFoundError, OSError) as e:
                logger.error(f"Failed to open the SSPL 'state.txt' file with an error '{e}',\
                    Can't determine the SSPL state, So enclosure logs also being collected.")
                sspl_state = 'active'

            self.get_ipmi_sel_data()
            self.get_config_data()
            self.get_drives_smart_data()
            if sspl_state == "active" and not include_encl:
                self.get_enclosure_logs()

            if os.path.exists(self.enclosure_log) and sspl_state == 'active' \
                    and not include_encl:
                enclosure_zip_file = "enclosure-wwn-{0}-logs-{1}.zip".format(
                    self.enclosure_wwn, str(int(time.time())))
                shutil.copy(self.enclosure_log,
                            self.localTempPath+enclosure_zip_file)
                logger.info("Enclosure Log File Location: %s" %
                            self.localTempPath+enclosure_zip_file)


        except (OSError, tarfile.TarError) as err:
            msg = "Facing problem while creating sspl support bundle : %s" % err
            self.__clear_tmp_files()
            raise SupportBundleError(1, msg)
        try:
            # Process request
            BundleRequestHandler._update_request_status(
                request_id, BundleRequestHandler.SUCCESS)
        except Exception as err:
            status = BundleRequestHandler.FAILED + f" - {err}"
            BundleRequestHandler._update_request_status(
                request_id, status)
        return request_id

    def get_ipmi_sel_data(self):
        ipmitool = IpmiFactory().get_implementor('ipmitool')
        res, err, retcode = ipmitool._run_ipmitool_subcommand("sel list")
        if retcode != 0:
            if err.find(ipmitool.VM_ERROR) != -1:
                err = ("Detected VM environment, can't reach BMC over inband"
                       "KCS channel, avoiding BMC data collection using IPMI.")
            logger.warn(
                f"Unable to fetch SEL list data with an error : {err}")
        else:
            with open(self.ipmi_sel_data, 'w+') as sel_list:
                sel_list.write(res)

    def get_config_data(self):
        os.makedirs(self.sspl_conf_dir, exist_ok=True)
        for conf_file in glob.glob('/etc/sspl*.*'):
            shutil.copy(conf_file, self.sspl_conf_dir)

    def _run_command(self, command):
        """Run the command and get the response and error returned"""
        process = subprocess.Popen(
            command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
        return_code = process.wait()
        response, error = process.communicate()
        return response.rstrip('\n'), error.rstrip('\n'), return_code

    def get_drives_smart_data(self):
        lsscsi_cmd = " ".join(["lsscsi", "|", "grep", "disk"])
        lsscsi_cmd = shlex.split(lsscsi_cmd)
        # lsscsi_response, _, _ = SimpleProcess(lsscsi_cmd).run()
        lsscsi_response, _, _ = self._run_command(lsscsi_cmd)
        os.makedirs(self.boot_drvs_dta, exist_ok=True)
        for res in lsscsi_response.split("\n"):
            drive_path = res.strip().split(' ')[-1]
            smartctl_cmd = f"sudo smartctl -a {drive_path} --json"
            # response, _, _ = SimpleProcess(smartctl_cmd).run()
            response, _, _ = self._run_command(smartctl_cmd)
            response = json.loads(response)
            try:
                if 'device' in response and response['device']['protocol'] == 'ATA':
                    file_name = drive_path.replace('/', '_')[1:]
                    with open(f"{self.boot_drvs_dta}/{file_name}.json", "w+") as fp:
                        json.dump(response, fp,  indent=4)

            except Exception as e:
                logger.error(
                    "Error in writing {0} file: {1}".format(response, e))

    def get_enclosure_logs(self):
        from framework.platforms.realstor.realstor_enclosure \
            import singleton_realstorencl
        url = singleton_realstorencl.build_url(
            singleton_realstorencl.URI_CLIAPI_BASE)
        COLLECTING_DEBUG_LOG_STARTED = False
        for encl_trigger_log_retry_index in range(0,
                                                  sspl_const.ENCL_TRIGGER_LOG_MAX_RETRY):
            response = singleton_realstorencl\
                .ws_request(url,
                            singleton_realstorencl.ws.HTTP_POST,
                            post_data=f'{singleton_realstorencl.URL_ENCLLOGS_POSTDATA}/"{sspl_const.SUPPORT_REQUESTOR_NAME}"{sspl_const.SUPPORT_EMAIL_ID}"{sspl_const.SUPPORT_CONTACT_NUMBER}')

            if not response:
                logger.error("{0}:: {2} status unavailable as ws request {1}"
                             " failed".format(singleton_realstorencl.LDR_R1_ENCL, url, "Debug log"))
                break

            elif response.status_code != singleton_realstorencl.ws.HTTP_OK:
                logger.error("{0}:: http request {1} to get {3} failed with"
                             " err {2} enclosure trigger log retry index {4}".format(singleton_realstorencl.LDR_R1_ENCL, url, response.status_code,
                                                                                     "Debug log", encl_trigger_log_retry_index))

            else:
                response_data = response.json()
                if response_data["status"][0]["response-type"] == "Success" and response_data["status"][0]["response"] == "Collecting debug logs.":
                    logger.info("Collecting enclosure debug logs in progress")
                    COLLECTING_DEBUG_LOG_STARTED = True
                    break
                else:
                    logger.error("{0}:: http request {1} to get {3} failed with"
                                 " response-type {2}".format(singleton_realstorencl.LDR_R1_ENCL, url, response_data["status"][0]["response-type"], "Debug log"))

        if COLLECTING_DEBUG_LOG_STARTED is True:
            self.enclosure_wwn = self.get_enclosure_wwn(singleton_realstorencl)
            url = singleton_realstorencl.build_url(
                singleton_realstorencl.URI_CLIAPI_DOWNLOADDEBUGDATA)
            for encl_download_retry_index in range(0, sspl_const.ENCL_DOWNLOAD_LOG_MAX_RETRY):
                response = singleton_realstorencl.ws_request(
                    url, singleton_realstorencl.ws.HTTP_GET)
                if not response:
                    logger.error("{0}:: {2} status unavailable as ws request {1}"
                                 " failed".format(singleton_realstorencl.LDR_R1_ENCL, url, "Debug log"))
                elif response.status_code != singleton_realstorencl.ws.HTTP_OK:
                    logger.error("{0}:: http request {1} to get {3} failed with"
                                 " err {2}".format(singleton_realstorencl.LDR_R1_ENCL, url, response.status_code, "Debug log"))
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
                            with open(self.enclosure_log, 'wb') as enclosure_resp:
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

    def get_enclosure_wwn(self, singleton_realstorencl):
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

    @staticmethod
    def _update_bundle_id(bundle_id: str, sspl_sb_id: str, tar_file: str):
        """Updates new request information with bundle specific attributes."""
        req_id = "sb_%s" % bundle_id
        req_info = {
            "sspl_sb_id": sspl_sb_id,
            "tar_file": tar_file,
            "time": datetime.strftime(
                datetime.now(), '%Y-%m-%d %H:%M:%S')
        }
        req_register.set(["%s" % req_id], [req_info])

    def _generate_tar(self, target_path: str, tar_name: str):
        """Generate tar.gz file at given path."""
        target_path = target_path if target_path is not None \
            else SupportBundle._default_path
        file_name = os.path.join(target_path, tar_name + '.tar.gz')
        file_name = tar_name + '.tar.gz'
        file_dir = file_name.replace(".tar.gz", "")
        tarfile_data = {
            self.sspl_log_dir: os.path.join(file_dir, "sspl/logs/"),
            self.sspl_conf_dir: os.path.join(file_dir, "sspl/config/"),
            self.boot_drvs_dta: os.path.join(file_dir, "drives_SMART_data/"),
            self.ipmi_sel_data: os.path.join(file_dir, "ipmi/ipmi_sel_data.txt"),
            sspl_const.DATA_PATH: os.path.join(file_dir, "sspl/data/"),
            self.iem_log_dir: os.path.join(file_dir, "iems/")
        }
        EXCLUDE_FILES = [sspl_const.SB_DATA_PATH]

        try:
            with tarfile.open(self.localTempPath+file_name, "w:gz") as tar:
                for key, value in tarfile_data.items():
                    if os.path.exists(key):
                        try:
                            tar.add(key, arcname=value,
                                    exclude=lambda x: x in EXCLUDE_FILES)
                        except IOError as err:
                            logger.error("Unable to include %s logs with an error %s"
                                         % (key, err))
        except (OSError, tarfile.TarError) as err:
            msg = "Facing problem while creating sspl support bundle : %s" % err
            self.__clear_tmp_files()
            raise SupportBundleError(1, msg)

    @staticmethod
    def __generate_file_names(bundle_id: str, bundle_time: str):
        """Will return a unique file name for every support bundle request."""
        Conf.load("cluster", SupportBundle._conf_file, skip_reload=True)
        cluster_conf = Conf.get("cluster", "server_node")
        cluster_id = cluster_conf["cluster_id"]
        hostname = SupportBundle.__get_private_hostname(cluster_conf)
        tar_name = "sspl_{0}_SN-{1}_Server-{2}_{3}".format(
            bundle_id, cluster_id, hostname, bundle_time,)

        file_name = "{0}.json".format(tar_name.replace("sspl_", "MS_")
                                      .replace(f"_{bundle_id}", "").replace("plus_", ""))
        return tar_name, file_name

    @staticmethod
    def __get_private_hostname(cluster_conf):
        """Returning private hostname."""
        try:
            private_fqdn = cluster_conf["network"]["data"]["private_fqdn"]
            hostname = private_fqdn.split(".")[0]
        except:
            hostname = "NA"
        return hostname

    @staticmethod
    def __clear_tmp_files():
        """Clean temporary files created by the support bundle."""
        shutil.rmtree(SupportBundle._tmp_src)
        if os.path.exists(sspl_const.SSPL_SB_TMP):
            shutil.rmtree(sspl_const.SSPL_SB_TMP)

    @staticmethod
    def parse_arguments():
        parser = argparse.ArgumentParser(description="SSPL Support Bundle")
        parser.add_argument('bundle_id', help='Unique bundle id')
        parser.add_argument('target_path', help='Path to store the created bundle',
                            nargs='?', default="/var/seagate/cortx/support_bundle/")
        parser.add_argument('-noencl', action='store_true',
                            help='Exclude enclosure logs')
        parser.add_argument('-console', action='store_true',
                            help='Print logs on console')
        args = parser.parse_args()
        return args


def initialize_logging(parser):
    # set Logging Handlers
    _logger = logging.getLogger('sspl_sb')
    logging_level = Conf.get(
        SSPL_CONF, f"{'SYSTEM_INFORMATION'}>{'log_level'}", "INFO")
    _logger.setLevel(logging_level)
    handler = logging.handlers.SysLogHandler(
        address=(sspl_const.SYSLOG_HOST, sspl_const.SYSLOG_PORT))
    syslog_format = "%(name)s[%(process)d]: " \
                    "%(levelname)s %(message)s (%(filename)s:%(lineno)d)"
    formatter = logging.Formatter(syslog_format)
    handler.setFormatter(formatter)
    _logger.addHandler(handler)

    # Add console handler
    if "-console" in parser:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        _logger.addHandler(console)
    return _logger


logger = initialize_logging(sys.argv)


def main():
    bundle = SupportBundle()
    args = bundle.parse_arguments()
    bundle.generate(args)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt as e:
        print(f"\n\nWARNING: User aborted command. Partial data "
              f"save/corruption might occur. It is advised to re-run the"
              f"command. {e}")
        sys.exit(1)
