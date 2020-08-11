import os
from time import sleep
from subprocess import call
from sspl_test.framework.base.sspl_constants import CONSUL_PATH


def kcs_channel_alert(active_bmc_IF_key,active_bmc_IF_value):
    system = "system"
    if active_bmc_IF_value != system:
        call(f"{CONSUL_PATH}/consul kv put {active_bmc_IF_key} {system}".split())
        sleep(.1)
    # disable kcs interface
    call("touch /tmp/kcs_disable".split())

def lan_channel_alert(active_bmc_IF_key,active_bmc_IF_value):
    lan = "lan"
    if active_bmc_IF_value != lan:
        call(f"{CONSUL_PATH}/consul kv put {active_bmc_IF_key} {lan}".split())
        sleep(.1)
    # disable lan interface
    call("touch /tmp/lan_disable".split())

def clean_previous_lan_alert(key,value):
    call(f"{CONSUL_PATH}/consul kv put {key}".split())
    sleep(.1)

def restore_config(key, value):
    if os.path.exists("/tmp/lan_disable"):
        call("rm -rf /tmp/lan_disable".split())
        sleep(.1)
    elif os.path.exists("/tmp/kcs_disable"):
        call("rm -rf /tmp/kcs_disable".split())
        sleep(.1)

    if value is not None:
        call(f"{CONSUL_PATH}/consul kv put {key} {value}".split())
    else:
        call(f"{CONSUL_PATH}/consul kv put {key}".split())
    sleep(.1)
