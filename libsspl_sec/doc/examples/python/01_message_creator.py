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

""" Example libsspl_sec usage. """
import ctypes
SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so')


def main():
    """ Mainline. """

    # get token (ie private key) for message signing.
    username = "jsmith"
    password = "p4sswd"
    authn_token_len = len(password) + 1
    session_length = 60 * 60  # 1h
    token = ctypes.create_string_buffer(SSPL_SEC.sspl_get_token_length())
    SSPL_SEC.sspl_generate_session_token(
        username, authn_token_len, password,
        session_length, token)

    # sign message
    message = "hello, world!"
    msg_len = len(message) + 1
    sig = ctypes.create_string_buffer(SSPL_SEC.sspl_get_sig_length())
    SSPL_SEC.sspl_sign_message(msg_len, message, username, token, sig)

    # do something with the message and signature here.  (ie write to a file,
    # socket, etc.)
    print("Message: '%s'" % message)
    print("Signature: '%s'" % sig.raw)


if __name__ == '__main__':
    main()
