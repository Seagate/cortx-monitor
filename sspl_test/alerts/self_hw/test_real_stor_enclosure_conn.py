# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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

import hashlib
import json
import time

# Checks connectivity to hw enclosure as part of hw self test
# Read current sspl config (ip, port, username, pw)
# Login to enclosure via webservice api request
# Retrive show system cmd info
import requests
from cortx.utils.security.cipher import Cipher
from cortx.utils.validator.v_controller import ControllerV
from cortx.utils.validator.v_network import NetworkV
from alerts.self_hw.self_hw_utilities import get_node_id
from framework.utils.conf_utils import (GLOBAL_CONF, Conf,
    ENCLOSURE, CNTRLR_PRIMARY_IP_KEY,
    CNTRLR_PRIMARY_PORT_KEY, CNTRLR_SECONDARY_IP_KEY, CNTRLR_SECONDARY_PORT_KEY,
    CNTRLR_USER_KEY, CNTRLR_SECRET_KEY, ENCLOSURE)
from framework.utils.encryptor import gen_key, decrypt

login_headers = {'datatype':'json'}
timeout = 20
HTTP_OK = 200
primary_ip = Conf.get(GLOBAL_CONF, CNTRLR_PRIMARY_IP_KEY)
secondary_ip = Conf.get(GLOBAL_CONF, CNTRLR_SECONDARY_IP_KEY)
primary_port = Conf.get(GLOBAL_CONF, CNTRLR_PRIMARY_PORT_KEY)
secondary_port = Conf.get(GLOBAL_CONF, CNTRLR_SECONDARY_PORT_KEY)
cntrlr_user = Conf.get(GLOBAL_CONF, CNTRLR_USER_KEY)
cntrlr_secret = Conf.get(GLOBAL_CONF, CNTRLR_SECRET_KEY)
cntrlr_key = gen_key(ENCLOSURE, "storage_enclosure")
cntrlr_passwd = decrypt(cntrlr_key, cntrlr_secret)


def show_system(ip, port, sessionKey):
    url = f"http://{ip}:{port}/api/show/system"
    # request headers for next request
    request_headers = {'datatype':'json','sessionKey':sessionKey}
    # make the request
    response = requests.get(url, headers=request_headers, timeout=timeout)
    print(response)
    try:
        # process the response
        if response and response.status_code == HTTP_OK:
            jresponse = json.loads(response.content)
            if jresponse['status'][0]['return-code'] == 0:
                print(jresponse)
            else:
                assert(False)
        else:
            assert(False)
    except:
        print("ERROR: Show system failed.")
        assert(False)

def init(args):
    pass

def test_real_stor_enclosure_conn(args):
    # Default to srvnode-1
    ip = primary_ip
    port = primary_port
    if get_node_id() == "srvnode-2":
        # Update
        ip = secondary_ip
        port = secondary_port

    # build url for primary
    cli_api_auth = cntrlr_user + '_' + cntrlr_passwd
    auth_hash = hashlib.sha256(cli_api_auth.encode('utf-8')).hexdigest()
    url = f"http://{ip}:{port}/api/login/{auth_hash}"

    try:
        # get request to url
        response = requests.get(url, headers=login_headers, timeout=timeout)
        # process the response
        if response and response.status_code == HTTP_OK:
            try:
                jresponse = json.loads(response.content)
            except ValueError as badjson:
                print("%s returned mal-formed json:\n%s" % (url, badjson))

            if jresponse['status'][0]['return-code'] == 1:
                sessionKey = jresponse['status'][0]['response']
                # show system
                show_system(ip, port, sessionKey)
            else:
                assert(False)
        else:
            assert(False)
    except Exception as e:
        print(f"Login to enclosure failed : {e}")
        assert(False)

def test_controller_reachability(args):
    NetworkV().validate("connectivity", [primary_ip, secondary_ip])

def test_controller_accessibility(args):
    c_validator = ControllerV()
    c_validator.validate(
        "accessible", [primary_ip, cntrlr_user, cntrlr_passwd])
    c_validator.validate(
        "accessible", [secondary_ip, cntrlr_user, cntrlr_passwd])

def test_firmware_version_ok(args):
    mc_expected = ["GN265", "GN280"]
    c_validator = ControllerV()
    c_validator.validate(
        "firmware", [primary_ip, cntrlr_user, cntrlr_passwd, mc_expected])
    c_validator.validate(
        "firmware", [secondary_ip, cntrlr_user, cntrlr_passwd, mc_expected])


test_list = [
    test_real_stor_enclosure_conn,
    test_controller_reachability,
    test_controller_accessibility,
    test_firmware_version_ok
    ]
