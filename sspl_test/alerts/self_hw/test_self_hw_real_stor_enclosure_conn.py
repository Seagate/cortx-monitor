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

# Checks connectivity to hw enclosure as part of hw self test
# Read current sspl config (ip, port, username, pw)
# Login to enclosure via webservice api request
# Retrive show system cmd info
import requests
import hashlib
import time
import json

from alerts.self_hw.self_hw_utilities import run_cmd, get_from_consul, get_node_id

from cortx.utils.security.cipher import Cipher
from framework.utils.conf_utils import (CLUSTER, CONTROLLER, CLUSTER_ID, ENCLOSURE,
                                        GLOBAL_CONF, IP, MGMT_INTERFACE,
                                        PASSWORD, POLLING_FREQUENCY, PORT,
                                        PRIMARY, SECONDARY, SRVNODE, SSPL_CONF,
                                        STORAGE, STORAGE_ENCLOSURE, USER, Conf)

def gen_key(cluster_id, service_name):
    ''' Generate key for decryption '''
    key = Cipher.generate_key(cluster_id, service_name)
    return key

def decrypt(key, text):
    ''' Decrypt the <text> '''
    return Cipher.decrypt(key, text).decode()

login_headers = {'datatype':'json'}
timeout = 20
HTTP_OK = 200

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
        print("Show system failed.")
        assert(False)

def init(args):
    pass

def test_self_hw_real_stor_enclosure_conn(args):
    # Default to srvnode-1
    ip = Conf.get(GLOBAL_CONF, f"{STORAGE}>{ENCLOSURE}>{CONTROLLER}>{PRIMARY}>{IP}")
    port = Conf.get(GLOBAL_CONF, f"{STORAGE}>{ENCLOSURE}>{CONTROLLER}>{PRIMARY}>{PORT}")
    if get_node_id() == "srvnode-2":
        # Update
        ip = Conf.get(GLOBAL_CONF, f"{STORAGE}>{ENCLOSURE}>{CONTROLLER}>{SECONDARY}>{IP}")
        port = Conf.get(GLOBAL_CONF, f"{STORAGE}>{ENCLOSURE}>{CONTROLLER}>{SECONDARY}>{PORT}")
    username = Conf.get(GLOBAL_CONF, f"{STORAGE}>{ENCLOSURE}>{CONTROLLER}>{USER}")
    passwd = Conf.get(GLOBAL_CONF, f"{STORAGE}>{ENCLOSURE}>{CONTROLLER}>{PASSWORD}")
    cluster_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{CLUSTER_ID}",'CC01')

    # decrypt the passwd
    decryption_key = gen_key(cluster_id, 'storage_enclosure')
    passwd = decrypt(decryption_key, passwd.encode('ascii'))

    # build url for primary
    cli_api_auth = username + '_' + passwd
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

test_list = [test_self_hw_real_stor_enclosure_conn]
