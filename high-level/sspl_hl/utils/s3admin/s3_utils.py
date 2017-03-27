# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2017 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.
# _author_ = "Vikram chhajer"

import os
import httplib
import urllib
import urlparse
import logging

import yaml
from boto3.session import Session
import plex.core.log as logger
import boto3

from sspl_hl.utils.strings import Strings


def enable_boto_logging():
    boto3.set_stream_logger(name='boto', level=logging.DEBUG)
    logging.basicConfig(filename='/var/log/boto.log', level=logging.DEBUG)
    logging.getLogger('boto').setLevel(logging.DEBUG)


# Create a new IAM serssion.
def get_session(access_key=None, secret_key=None, session_token=None):
    return Session(aws_access_key_id=access_key,
                   aws_secret_access_key=secret_key,
                   aws_session_token=session_token)


def get_endpoint(service):
    endpoints_file = os.path.join(Strings.ENDPOINTS_CONFIG_PATH)
    with open(endpoints_file, 'r') as f:
        endpoints = yaml.safe_load(f)
        server = endpoints[service]
        found = False
        for url in server:
            try:
                urllib.urlopen(url).getcode()
                found = True
                return url
            except Exception:
                logger.debug("Server %s is not running. Trying next" % url)
                continue
    if not found:
        raise


# Create an IAM client.
def get_client(access_key, secret_key, session_token, service):
    try:
        session = get_session(access_key, secret_key)
        url = get_endpoint(service)
        return session.client(service, use_ssl='false',
                              endpoint_url=url)
    except Exception:
        raise


def execute_cmd(client, parameters):
    auth_endpoint = client._endpoint.host
    auth_server_name = urlparse.urlparse(auth_endpoint).netloc
    params = urllib.urlencode(parameters)
    headers = {"Content-type": "application/x-www-form-urlencoded",
               "Accept": "text/plain"}
    conn = httplib.HTTPConnection(auth_server_name)
    conn.request("POST", "/", params, headers)
    response = conn.getresponse()
    data = response.read()
    conn.close()
    return response, data


class CommandResponse():
    def __init__(self, status=None, response=None, msg=None):
        self.status = status
        self.msg = msg
        self.response = response

    def __call__(self, *args, **kwargs):
        return self
