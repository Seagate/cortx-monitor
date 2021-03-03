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

from time import sleep
from subprocess import call


def create_nw_interface():
    # Load the dummy interface module
    call("modprobe dummy".split())
    sleep(.1)
    call("ip link add eth-mocked type dummy".split())
    sleep(.1)
    # Create a dummy interface called dummy1
    call("ip link set name eth-mocked dev dummy0".split())
    sleep(.1)
    call("ip link add br0 type bridge".split())
    sleep(.1)
    # TODO: Replace with non-offensive terms when possible.
    # An email was sent on 18082020 to stephen@networkplumber.org requesting this
    call("ip link set dev eth-mocked master br0".split())


def shuffle_nw_interface():
    create_nw_interface()
    sleep(3)
    # Change interface's state from down to up
    # Default state for eth-mocked and br0 is down.
    call("ip link set eth-mocked up".split())
    sleep(.1)
    call("ip link set br0 up".split())
