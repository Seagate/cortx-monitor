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
    sleep(.1)
    call("ip link add br0 type bridge".split())
    sleep(.1)
    call("ip link set dev eth-mocked master br0".split())


def shuffle_nw_interface():
    create_nw_interface()
    sleep(.2)
    # Change interface's state from up/down to down/up
    call("ip link set eth-mocked up".split())
    call("ip link set br0 up".split())
    sleep(2)
    call("ip link set eth-mocked down".split())
    call("ip link set br0 down".split())
    sleep(.2)

def delete_nw_interface():
    call("ip link delete eth-mocked".split())
    call("ip link delete br0".split())
