"""
 ****************************************************************************
 Filename:          utils.py
 Description:       Util functions for messaging
 Creation Date:     08/06/2020
 Author:            Sandeep Anjara

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from framework.utils import encryptor
from framework.utils.config_reader import ConfigReader
from framework.base.sspl_constants import ServiceTypes, COMMON_CONFIGS, \
    AMQP_EXCHANGE_TYPE_TOPIC, AMQP_PORT, MESSAGING, MESSAGING_TYPE_RABBITMQ, \
    MESSAGING_CLUSTER_SECTION


SYSTEM_INFORMATION_KEY = 'SYSTEM_INFORMATION'
CLUSTER_ID_KEY = 'cluster_id'
MESSAGING_CLUSTER_HOSTS_KEY = 'cluster_nodes'
EGRESSPROCESSOR = 'EGRESSPROCESSOR'
conf_reader = ConfigReader()

messaging_bus_type = conf_reader._get_value_with_default(section=MESSAGING, 
                            key="type", default_value=MESSAGING_TYPE_RABBITMQ)

# MESSAGING classes have diffrent attributes than sspl config
# This mapping specifies what sspl config to use for MESSAGING
# class attibute
messaging_attibute_config_maping = {
    "exchange_name": "exchange",
    "queue_name": "exchange_queue"
}

# Common values are used from EGRESSPROCESSOR
password = conf_reader._get_value_with_default(section=EGRESSPROCESSOR, 
                                    key="password", default_value="sspl4ever")
cluster_id = conf_reader._get_value_with_default(SYSTEM_INFORMATION_KEY,
                COMMON_CONFIGS.get(SYSTEM_INFORMATION_KEY).get(CLUSTER_ID_KEY),'')
decryption_key = encryptor.gen_key(cluster_id, ServiceTypes.__members__[messaging_bus_type.upper()].value)
hosts = conf_reader._get_value_list(MESSAGING_CLUSTER_SECTION, 
                    COMMON_CONFIGS.get(MESSAGING_CLUSTER_SECTION).get(MESSAGING_CLUSTER_HOSTS_KEY))
username = conf_reader._get_value_with_default(section=EGRESSPROCESSOR, 
                                    key="username", default_value="sspluser")
password = encryptor.decrypt(decryption_key, password.encode('ascii'), MESSAGING)

messaging_common_config = {
        "hosts": hosts,
        "port": AMQP_PORT,
        "username": username,
        "password": password,
        "durable": True,
        "exclusive": False,
        "exchange_type": AMQP_EXCHANGE_TYPE_TOPIC,
        "retry_count": 1
        }

def get_messaging_config(section, keys):
    """
    Merge common and module specific configs.

    @param section: configuration section
    @param keys: list of tuples containing key and default value
    @retrun : merged configuration
    """
    config = {}
    for key, default_value in keys:
        config[messaging_attibute_config_maping.get(key, key)] = \
            conf_reader._get_value_with_default(section, key, default_value)
    return {**messaging_common_config, **config}
