"""
 ****************************************************************************
 Filename:          mon_utils.py
 Description:       Common utility functions required for encryption purpose
 Creation Date:     04/02/2020
 Author:            Malhar Vora

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from eos.utils.security.cipher import Cipher, CipherInvalidToken
from framework.utils.service_logging import logger


def gen_key(cluster_id, service_name):
    # Generate key for decryption
    key = Cipher.generate_key(cluster_id, service_name)
    return key


def encrypt(key, text):
    '''Encrypt sensitive data. Ex: RabbitMQ credentials'''
    # Before encrypting text we need to convert string to bytes using encode()
    # method
    return Cipher.encrypt(key, text.encode())


def decrypt(key, text, caller=None):
    '''Decrypt the <text>'''
    decrypt_text = text
    try:
        decrypt_text = Cipher.decrypt(key, text).decode()
        return decrypt_text
    except CipherInvalidToken as e:
        logger.error("{0}:Password decryption failed requested by {1}.".format(e, caller))
        return decrypt_text.decode()
