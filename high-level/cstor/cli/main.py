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

""" This file acts as the main executable for the Castor CLI
"""

# Import system Modules

# Import Local Modules

from cstor.cli.commands.command_factory import Factory
from cstor.cli.errors import BaseError, CommandTerminated


def main():
    """ Main script to execute the CLI commands and print the
    result back to the terminal.
    -h option should be used to get the help on the usage of
    this script
    """

    try:
        command_obj = Factory.get_subcmd()
        result = command_obj.execute_action()
        if result and isinstance(result, list):
            for item in result:
                print item
        elif result and isinstance(result, dict):
            for key in result:
                print key + ": " + str(result.get(key))
        else:
            if result is not None:
                print result
    except CommandTerminated:
        print 'Command is terminated'
    except BaseError as extra_info:
        print "Error: {}.\nDesc: {}".format(extra_info.err, extra_info.desc)


if __name__ == '__main__':
    main()
