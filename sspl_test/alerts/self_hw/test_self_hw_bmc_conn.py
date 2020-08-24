# Connectivity to BMC is checked via SSPL during restart
# We can restart SSPL and wait for an alert from SSPL if there is a failure
# If there is no failure, that would mean connectivity is OK
import os
from sspl_test.framework.base.sspl_constants import SSPL_TEST_PATH

def init(args):
    pass

# As part of start_checker, during sspl restart, BMC unreachable alert is monitored
# If alert is found, a file will be created
# Check for that file in sspl_test/
def test_self_hw_bmc_connectivity(args):
    if os.path.exists(f"{SSPL_TEST_PATH}/self_hw_bmc_error.txt"):
        # fail the test
        assert(False)


test_list = [test_self_hw_bmc_connectivity]


