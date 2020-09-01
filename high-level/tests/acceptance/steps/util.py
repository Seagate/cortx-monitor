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

""" A collection of utility functions that are useful for the acceptance tests.
"""
import lettuce
import time


@lettuce.world.absorb
def wait_for_condition(
        status_func, max_wait, timeout_message="Timeout Expired", step=0.1
):
    """ Waits for the specified condition to become true.

    This function repeatedly calls status_func().  When status_func() returns
    true, then this function returns.  Otherwise, the function will be called
    repeatedly until it either returns true, or the max_wait timeout expires,
    at which point, a RuntimeError will be thrown.

    @type status_func:            Function pointer
    @param status_func:           A function pointer that returns true when
                                  we've successfully completed waiting.
    @param max_wait:              Number of seconds to wait for the condition
                                  to become true.
    @param timeout_message:       Message to be placed in the RuntimeError
                                  should the timeout expire.
    @param step:                  Amount of time to sleep in between calls to
                                  the status_func function.
    @raise RuntimeError:          Raised if the timeout expires.
    """
    while not status_func():
        if max_wait <= 0:
            raise RuntimeError(timeout_message)
        time.sleep(step)
        max_wait -= step
