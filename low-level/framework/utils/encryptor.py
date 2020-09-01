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

"""
 ****************************************************************************
  Description:       Common utility functions required for encryption purpose
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
