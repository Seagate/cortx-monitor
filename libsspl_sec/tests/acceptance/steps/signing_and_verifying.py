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

""" Implement lettuce steps for signing_and_verifying.feature. """
import lettuce
import subprocess


@lettuce.step(u'Given I set the method to be \'([^\']*)\'')
def set_method(_, method_name):
    """ Override the default encryption method. """
    lettuce.world.method_name = method_name


@lettuce.step(u'my username is "([^"]*)"')
def my_username_is_group1(_, username):
    """ Record username for later use. """
    lettuce.world.username = username


@lettuce.step(u'And my passord is "([^"]*)"')
def and_my_passord_is_group1(_, password):
    """ Record password for later use. """
    lettuce.world.password = password


@lettuce.step(u'When I generate a session token')
def when_i_generate_a_session_token(_):
    """ Run ./helpers/generate_session_token to acquire a session token.

    The token will be used later to sign messages.
    """
    lettuce.world.encoded_session_token = subprocess.check_output([
        './helpers/generate_session_token',
        '--method', lettuce.world.method_name,
        lettuce.world.username,
        lettuce.world.password
        ]).strip()


@lettuce.step(u'And I sign the following message with my session token:')
def sign_message_with_session_token(step):
    """ Run ./helpers/sign_message to sign a message.

    The resulting signature will be stored for later use.
    """
    cmd = [
        './helpers/sign_message',
        '--method', lettuce.world.method_name,
        lettuce.world.username,
        lettuce.world.encoded_session_token
        ]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE
        )
    lettuce.world.message = step.multiline.strip()
    lettuce.world.encoded_sig = \
        proc.communicate(lettuce.world.message)[0].strip()
    assert proc.returncode == 0


@lettuce.step(u'Then the message can be verified as authentic.')
def verify_message(_):
    """ Use ./helpers/verify_message to verify previously generated sig. """
    cmd = [
        './helpers/verify_message',
        '--method', lettuce.world.method_name,
        lettuce.world.username,
        lettuce.world.encoded_sig
        ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    proc.communicate(lettuce.world.message)
    assert proc.returncode == 0, \
        "Non-zero return code (%i) from verify_message." % proc.returncode
