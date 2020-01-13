#!/usr/bin/env python
from time import sleep
from subprocess import call

def create_nw_interface():
    # Load the dummy interface module
    call("modprobe dummy".split())
    sleep(.1)
    # Create a dummy interface called dummy1
    call("ip link set name eth-mocked dev dummy0".split())
    sleep(.1)
    call("ip link add eth-mocked type dummy".split())

def shuffle_nw_interface():
    create_nw_interface()
    sleep(.2)
    # Change interface's state from up/down to down/up
    call("ip link set eth-mocked up".split())
    sleep(2)
    call("ip link set eth-mocked down".split())
    sleep(.2)

def delete_nw_interface():
    call("ip link delete eth-mocked".split())