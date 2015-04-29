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
