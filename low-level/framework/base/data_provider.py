
import subprocess
import ast
import configparser

PRODUCT_FAMILY = 'cortx'
COMM_CONFIG_FILE = f'/opt/seagate/{PRODUCT_FAMILY}/sspl/conf/common_config.ini'
SERVER_TYPE = 'virtual'
STORAGE_TYPE = 'virtual'
NODE_KEY_ID = 'srvnode-1'


def cmd_execute(cmd):
    result = subprocess.Popen(cmd,
            stdout=subprocess.PIPE).communicate()[0].decode("utf-8").rstrip()
    return result

def get_setup_info():
    cmd = ['sudo', '/usr/bin/provisioner', 'get_setup_info']
    try:
        setup_info = cmd_execute(cmd)
        setup_info = ast.literal_eval(setup_info)
    except:
        setup_info = dict()
    return setup_info

def get_consul_value(key):
    cmd = ['consul', 'kv', 'get', key]
    result = cmd_execute(cmd)
    return result

def read_common_config(key):
    section, stripped_key = key.split("/")
    try:
        config = configparser.ConfigParser()
        config.read(COMM_CONFIG_FILE)
        value = config[section.upper()][stripped_key]
    except:
        value = ''
    return value


setup_info = get_setup_info()

# get server_type i.e. "physical"", "virtual"
value_from_consul = get_consul_value('sspl/config/STORAGE_ENCLOSURE/type')
value_from_setup = setup_info.get('server_type', SERVER_TYPE).lower()
server_type =  value_from_consul or value_from_setup

# get storage_type i.e. "jbod", "rbod", "virtual"
value_from_consul = get_consul_value('sspl/config/SYSTEM_INFORMATION/type')
value_from_setup = setup_info.get('storage_type', STORAGE_TYPE).lower()
storage_type =  value_from_consul or value_from_setup

# get cluster_id
value_from_consul = get_consul_value('system_information/cluster_id') or \
                    get_consul_value('sspl/config/SYSTEM_INFORMATION/cluster_id')
value_from_config = read_common_config('SYSTEM_INFORMATION/cluster_id')
cluster_id =  value_from_consul or value_from_config

# get node_id
value_from_consul = get_consul_value(f'system_information/{NODE_KEY_ID}/node_id') or \
                    get_consul_value(f'sspl/config/SYSTEM_INFORMATION/{NODE_KEY_ID}/node_id')
value_from_config = read_common_config('SYSTEM_INFORMATION/node_id')
node_id =  value_from_consul or value_from_config
