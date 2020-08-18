#!/usr/bin/python

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

import sys

# mco rpc runcmd rc cmd=\"{}\" -F role=cc
# mco rpc runcmd rc cmd=\"{}\" -F role=storage
# mco find -F role=storage

if len(sys.argv) > 5:
    print 'Command executed successfully'
elif len(sys.argv) > 3:

    if (sys.argv[1] == 'ping') and \
            (sys.argv[2] == '-F') and \
            (sys.argv[3] == 'role=storage'):
        print ('vmc-rekvm-ssu-1-5\ttime=25.32 ms')
        print ('vmc-rekvm-ssu-1-6\ttime=25.76 ms')
        print ('vmc-rekvm-ssu-1-1\ttime=26.12 ms')
        print ('vmc-rekvm-ssu-1-4\ttime=26.47 ms')
        print ('vmc-rekvm-ssu-1-3\ttime=26.84 ms')
        print ('vmc-rekvm-ssu-1-2\ttime=27.20 ms')
        print ('\n---- ping statistics ----')
        print ('6 replies max: 27.95 min: 24.68 avg: 26.54')
    elif (sys.argv[1] == 'find') and \
            (sys.argv[2] == '-F') and \
            (sys.argv[3] == 'role=storage'):
        print ('vmc-rekvm-ssu-1-2')
        print ('vmc-rekvm-ssu-1-1')
        print ('vmc-rekvm-ssu-1-6')
        print ('vmc-rekvm-ssu-1-3')
        print ('vmc-rekvm-ssu-1-5')
        print ('vmc-rekvm-ssu-1-4')
    elif (sys.argv[1] == 'rpc') and \
            (sys.argv[2] == 'runcmd') and \
            (sys.argv[3] == 'rc'):
        print ('vmc-rekvm-ssu-1-1')
        print ('Output : 0')
        print ('vmc-rekvm-ssu-1-2')
        print ('Output : 0')
        print ('vmc-rekvm-ssu-1-3')
        print ('Output : 0')
else:
    print

sys.exit(0)
