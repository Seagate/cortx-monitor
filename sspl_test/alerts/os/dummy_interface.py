#!/usr/bin/env python
from time import sleep
from subprocess import call

def create_interface():
    # Load the dummy interface module
    call("modprobe dummy".split())
    sleep(.1)
    # Create a dummy interface called dummy1
    call("ip link set name dummy1 dev dummy0".split())
    sleep(.1)
    call("ip link add dummy1 type dummy".split())
    sleep(.2)
    # Change interface's state from up/down to down/up
    call("ip link set dummy1 up".split())
    sleep(2)
    call("ip link set dummy1 down".split())
    sleep(.2)


def delete_interface():
    call("ip link delete dummy1".split())