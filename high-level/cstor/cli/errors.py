#!/usr/bin/python3.6
# -*- coding: utf-8 -*-

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
    This file will contain all the exceptions that will be raised by cli
    client.
    Ideally, CLI should only raise and catch these exceptions.
"""

# Import system Modules

# Import Local Modules


class BaseError(Exception):
    """
        Parent class for the cli error classes
    """
    err = "Internal Error"
    desc = "Could not execute the command"

    def __init__(self, err=None, desc=None):
        super(BaseError, self).__init__()
        self.err = err or self.err
        self.desc = desc or self.desc


class CommandTerminated(KeyboardInterrupt):
    """
        This error will be raised when some command is terminated during
        the processing
    """
    err = "Command Terminated"
    desc = "Command is cancelled"

    def __init__(self, err=None, desc=None):
        super(CommandTerminated, self).__init__(err, desc)


class InvalidResponse(BaseError):
    """
        This error will be raised when an invalid response
        message is received for any of the cli commands.
    """
    err = "Invalid response"
    desc = "Invalid response message received " \
           "or the response message could not be parsed correctly"

    def __init__(self, err=None, desc=None):
        super(InvalidResponse, self).__init__(err, desc)


class InternalError(BaseError):
    """
    This error is raised by CLI for all unknown internal errors
    """

    err = "Internal Error"
    desc = 'An Internal error has occurred, unable to complete command.'

    def __init__(self, err=None, desc=None):
        super(InternalError, self).__init__(err, desc)


class InvalidArgumentError(BaseError):
    """
    This error is raised by CLI for all unknown internal errors
    """

    err = "Invalid input error"
    desc = 'Invalid input provided. Please enter valid input.'

    def __init__(self, err=None, desc=None):
        super(InvalidArgumentError, self).__init__(err, desc)
