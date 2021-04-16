#!/usr/bin/python3.6

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
   Encryption utility for information for SSPL.

   This script uses a Seagate proprietary package called cortx-py-utils. This
   package internally uses a symmetric key encryption algorithm called fernet.
   Read more about fernet at
       1. https://cryptography.io/en/latest/fernet/
       2. https://github.com/fernet/spec  in the Spec.md file

   Install package using following command:

   yum install -y cortx-py-utils

   TODO: Understand fernet terminologies and provide hint for errors based on
         those terminologies.
"""
import sys

try:
    from cortx.utils.security.cipher import Cipher
except ImportError as import_error:
    print('Error: cortx-py-utils is not installed.',
          'Please install using yum install -y cortx-py-utils')


def gen_key(unique_seed, root_node):
    ''' Generate key for decryption '''
    key = Cipher.generate_key(unique_seed, root_node)
    return key


def encrypt(key, text):
    ''' Encrypt sensitive data. Ex: RabbitMQ credentials '''
    # Before encrypting text we need to convert string to bytes using encode()
    # method
    return Cipher.encrypt(key, text.encode())


def decrypt(key, text):
    ''' Decrypt the <text> '''
    return Cipher.decrypt(key, text.encode("utf-8")).decode("utf-8")


def usage():
    ''' Print usage '''
    print("encryptor.py <encrypt|decrypt> <text> <cluster-id> <service-name>")


def main(args):
    ''' Main function '''
    ret_code = 0
    if len(args) != 4:
        print('Invalid arguments')
        usage()
        ret_code = 1
    else:
        try:
            operation = args[0].lower()
            text = args[1]
            cluster_id = args[2]
            service_name = args[3]
            print(f'operation: {text}')
            key = gen_key(str(cluster_id), service_name)
            print(f'Key => {key.decode()}\n')
            if operation == 'encrypt':
                encrypted_text = encrypt(key, text)
                print('Encryptext Text:')
                print(encrypted_text)
            elif operation == 'decrypt':
                decrypted_text = decrypt(key, text.encode('ascii'))
                print('Decryptext Text:')
                print(decrypted_text)
        except Exception as exc:
            ret_code = 1
            print(f'Error: {exc}')
    return ret_code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
