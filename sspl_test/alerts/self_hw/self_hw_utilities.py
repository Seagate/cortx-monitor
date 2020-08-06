# This file contains some utility functions/globals
# commonly used in hw self test
import subprocess

def run_cmd(cmd):
    subout = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = subout.stdout.readlines()
    return result

def get_from_consul(cmd):
    result = run_cmd(cmd)
    return result[0].decode().strip()

def is_virtual():
    cmd = "facter is_virtual"
    retVal = False
    result = run_cmd("facter is_virtual")
    if result:
        if 'true' in result[0].decode():
            retVal = True
    return retVal

def get_node_id():
        GRAINS_GET_NODE_CMD = "salt-call grains.get id --output=newline_values_only"
        MINION_GET_NODE_CMD = "cat /etc/salt/minion_id"
        node_key = 'srvnode-1'
        try:
            subout = subprocess.Popen(GRAINS_GET_NODE_CMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = subout.stdout.readlines()
            if result == [] or result == "":
                print(f"Command '{GRAINS_GET_NODE_CMD}' failed to fetch grain id or hostname.")
                subout = subprocess.Popen(MINION_GET_NODE_CMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                result = subout.stdout.readlines()
                if result == [] or result == "":
                    print(f"Command '{MINION_GET_NODE_CMD}' failed to fetch minion id or hostname.")
                    print("Using node_id ('srvnode-1') as we are not able to fetch it from hostname command.")
                    node_key = 'srvnode-1'
                else:
                    node_key = result[0].decode().rstrip('\n').lower()
            else:
                node_key = result[0].decode().rstrip('\n')
        except Exception as e:
            print(f"Can't read node id, using 'srvnode-1' : {e}")
        return node_key
