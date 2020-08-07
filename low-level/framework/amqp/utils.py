"""
 ****************************************************************************
 Filename:          utils.py
 Description:       Util functions for amqp
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
from framework.base.sspl_constants import ServiceTypes, COMMON_CONFIGS


SYSTEM_INFORMATION_KEY = 'SYSTEM_INFORMATION'
CLUSTER_ID_KEY = 'cluster_id'
AMQP_CLUSTER_SECTION = 'AMQPCLUSTER'
AMQP_CLUSTER_HOSTS_KEY = 'cluster_nodes'
EGRESSPROCESSOR = 'EGRESSPROCESSOR'
conf_reader = ConfigReader()

amqp_type = conf_reader._get_value_with_default(section="AMQP", 
                            key="type", default_value="rabbitmq")


def get_amqp_common_config():
    password = conf_reader._get_value_with_default(section=EGRESSPROCESSOR, 
                                    key="password", default_value="sspl4ever")
    cluster_id = conf_reader._get_value_with_default(SYSTEM_INFORMATION_KEY,
                COMMON_CONFIGS.get(SYSTEM_INFORMATION_KEY).get(CLUSTER_ID_KEY),'')
    
    decryption_key = encryptor.gen_key(cluster_id, 
                        ServiceTypes.__members__[amqp_type.upper()].value)
    return {
        "hosts": conf_reader._get_value_list(AMQP_CLUSTER_SECTION, 
                    COMMON_CONFIGS.get(AMQP_CLUSTER_SECTION).get(AMQP_CLUSTER_HOSTS_KEY)),
        "port": 5672,
        "username": conf_reader._get_value_with_default(section=EGRESSPROCESSOR, 
                                    key="username", default_value="sspluser"),
        "password": encryptor.decrypt(decryption_key, password.encode('ascii'), "AMQP")
        }