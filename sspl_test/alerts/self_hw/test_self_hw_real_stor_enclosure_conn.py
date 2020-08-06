# Checks connectivity to hw enclosure as part of hw self test
# Read current sspl config (ip, port, username, pw)
# Login to enclosure via webservice api request
# Retrive show system cmd info
import requests
import hashlib
import time
import json

from alerts.self_hw.self_hw_utilities import run_cmd, get_from_consul, get_node_id
from sspl_test.framework.base.sspl_constants import GET_PRIMARY_IP, GET_PRIMARY_PORT, \
    GET_USERNAME, GET_PASSWD, GET_CLUSTER_ID, GET_SECONDARY_IP, GET_SECONDARY_PORT

from eos.utils.security.cipher import Cipher

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
    ip = get_from_consul(GET_PRIMARY_IP)
    port = get_from_consul(GET_PRIMARY_PORT)
    if get_node_id() == "srvnode-2":
        # Update
        ip = get_from_consul(GET_SECONDARY_IP)
        port = get_from_consul(GET_SECONDARY_PORT)
    username = get_from_consul(GET_USERNAME)
    passwd = get_from_consul(GET_PASSWD)
    cluster_id = get_from_consul(GET_CLUSTER_ID)

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
