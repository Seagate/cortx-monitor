#!/usr/bin/env bash

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


# Change the permissions of he script in sspl-hl.spec file
if [ $1 = "poweron" ]
then
    echo discovering kvm nodes
    echo qemu+tcp://192.168.0.1:16509/system
    echo Nodes with role storage:
    echo vmc-rekvm-castor-kvm001-05
    echo vmc-rekvm-castor-kvm001-04
    echo vmc-rekvm-castor-kvm001-03
    echo vmc-rekvm-castor-kvm001-06
    echo vmc-rekvm-castor-kvm001-02
    echo vmc-rekvm-castor-kvm001-01
    echo It took 8 seconds to complete this task...
elif [ $1 = "poweroff" ]
then
    echo qemu+tcp://192.168.0.1:16509/system
    echo Nodes with role storage:
    echo vmc-rekvm-castor-kvm001-05
    echo vmc-rekvm-castor-kvm001-04
    echo vmc-rekvm-castor-kvm001-03
    echo vmc-rekvm-castor-kvm001-06
    echo vmc-rekvm-castor-kvm001-02
    echo vmc-rekvm-castor-kvm001-01
    echo It took 8 seconds to complete this task...
elif [ $1 = "status" ]
then
    echo 172.16.2.101
    echo Chassis Power is on
    echo 172.16.2.102
    echo Chassis Power is on
    echo 172.16.2.103
    echo Chassis Power is on
    echo 172.16.2.104
    echo Chassis Power is on
    echo It took 24 seconds to complete this task...
fi