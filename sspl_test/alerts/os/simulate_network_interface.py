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
    call("ip link set dev eth-mocked master br0".split())


def shuffle_nw_interface():
    create_nw_interface()
    sleep(3)
    # Change interface's state from down to up
    # Default state for eth-mocked and br0 is down.  
    call("ip link set eth-mocked up".split())
    call("ip link set br0 up".split())
