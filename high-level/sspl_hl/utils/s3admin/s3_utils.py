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
import socket
import hmac
import base64
from hashlib import sha1

import yaml
from boto3.session import Session
import plex.core.log as logger
import boto3

from sspl_hl.utils.strings import Strings

# Default timeout for checking server is available or not
socket.setdefaulttimeout(15)


def enable_boto_logging():
    """
    Enable botocore logging.

    It is used for debugging purpose.
    """
    boto3.set_stream_logger(name='boto', level=logging.DEBUG)
    logging.basicConfig(filename='/var/log/boto.log', level=logging.DEBUG)
    logging.getLogger('boto').setLevel(logging.DEBUG)


# Create a new IAM serssion.
def get_session(access_key=None, secret_key=None, session_token=None):
    """
    Get S3 Auth Session.
    """
    return Session(aws_access_key_id=access_key,
                   aws_secret_access_key=secret_key,
                   aws_session_token=session_token)


def get_endpoint(service):
    """
    This will find IAM Server endpoint.
    """
    endpoints_file = os.path.join(Strings.ENDPOINTS_CONFIG_PATH)
    with open(endpoints_file, 'r') as f:
        endpoints = yaml.safe_load(f)
        server = endpoints[service]
        logger.info("Server for %s service: %s " % (service, server))
        found = False
        if server is None:
            raise Exception("No Auth servers configured.")
        for url in server:
            try:
                logger.info("Checking %s " % url)
                urllib.urlopen(url).getcode()
                found = True
                logger.info("Returning %s " % url)
                return url
            except Exception:
                logger.debug("Server %s is not running. Trying next" % url)
                continue
    if not found:
        raise Exception("Unable to communicate to Auth servers.")


# Create an IAM client.
def get_client(access_key=None, secret_key=None, service=None):
    """
    Create IAM Client based on Access and Secret Key.

        This client will be used for all S3 related operations.
    """
    try:
        session = get_session(access_key, secret_key)
        url = get_endpoint(service)
        return session.client(service, use_ssl='false',
                              endpoint_url=url), None
    except IOError as ex:
        logger.info("Endpoints File not found")
        response = CommandResponse(status=-1, msg="IAM Auth servers "
                                                  "are not configured.")
    except Exception as ex:
        logger.info("Exception while fetching endpoint: %s" % (str(ex)))
        response = CommandResponse(status=-1, msg=str(ex))
    return None, response


def execute_cmd(client, parameters, headers=None):
    """
    Execute Account related commands.
    """

    if headers is None:
        headers = {"Content-type": "application/x-www-form-urlencoded",
                   "Accept": "text/plain"}

    auth_endpoint = client._endpoint.host
    auth_server_name = urlparse.urlparse(auth_endpoint).netloc
    params = urllib.urlencode(parameters)
    conn = httplib.HTTPConnection(auth_server_name)
    conn.request("POST", "/", params, headers)
    response = conn.getresponse()
    data = response.read()
    conn.close()
    return response, data


def utf8_encode(msg):
    """
    Encode string to UTF-8
    :param msg:
    :return:
    """
    return msg.encode('UTF-8')


def utf8_decode(msg):
    """
    Decode string to UTF-8
    :param msg:
    :return:
    """
    return str(msg).encode('UTF-8')


# if x-amz-* has multiple values then value for that header should be passed as
# list of values eg. headers['x-amz-authors'] = ['Jack', 'Jelly']
# example return value: x-amz-authors:Jack,Jelly\nx-amz-org:Seagate\n
def _get_canonicalized_xamz_headers(headers):
    xamz_headers = ''
    for header in sorted(headers.keys()):
        if header.startswith("x-amz-"):
            if type(headers[header]) is str:
                xamz_headers += header + ":" + headers[header] + "\n"
            elif type(headers[header]) is list:
                xamz_headers += header + ":" + ','.join(headers[header]) + "\n"

    return xamz_headers


def _create_str_to_sign(http_method, canonical_uri, params, headers):
    """
    Generating Header for Authentication
    """
    str_to_sign = http_method + '\n'
    str_to_sign += headers.get("content-md5", "") + "\n"
    str_to_sign += headers.get("content-type", "") + "\n"
    str_to_sign += headers.get("date", "") + "\n"
    str_to_sign += _get_canonicalized_xamz_headers(headers)
    str_to_sign += canonical_uri
    str_to_sign = utf8_encode(str_to_sign)
    return str_to_sign


def sign_request_v2(access_key, secret_key, method='GET', canonical_uri='/',
                    params={}, headers={}):
    """
    Signing request with authentication
    """
    str_to_sign = _create_str_to_sign(method, canonical_uri, params, headers)
    signature = utf8_decode(base64.encodestring(
        hmac.new(utf8_encode(secret_key), str_to_sign, sha1).digest()).strip())
    auth_header = "AWS %s:%s" % (access_key, signature)
    return auth_header


class CommandResponse():
    """
    Wrapper response class.

    This will be used to wrap response received from Auth server and send it to
    client.
    """

    def __init__(self, status=None, response=None, msg=None):
        self.status = status
        self.msg = msg
        self.response = response

    def __call__(self, *args, **kwargs):
        return self
