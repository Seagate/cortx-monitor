#!/usr/bin/python3.6

# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.


#############################################################
# Setup rabbitmq for use by sspl_ll on LDR_R1, LDR_R2 systems
# This script uses ConfStore as the source of the parameters.
# Usage:
#    python3 sspl_rabbitmq_reinit.py <product>
#############################################################

import subprocess
import sys
import pika

# using cortx package
from framework.base.sspl_constants import (cs_legacy_products,
                                           enabled_products,
                                           ServiceTypes,
                                           SSPL_CONFIG_INDEX,
                                           GLOBAL_CONFIG_INDEX)
from cortx.utils.security.cipher import Cipher, CipherInvalidToken
from cortx.utils.conf_store import Conf

RABBITMQCTL = '/usr/sbin/rabbitmqctl'
SECTION="EGRESSPROCESSOR"
INGRESS_CONFIG_SECTION = 'INGRESSPROCESSOR'
EGRESS_CONFIG_SECTION = 'EGRESSPROCESSOR'
LOGGER_CONFIG_SECTION = 'LOGGINGPROCESSOR'

EXCHANGE_NAME_KEY = 'exchange_name'
QUEUE_NAME_KEY = 'queue_name'
ROUTING_KEY = 'routing_key'
ACK_QUEUE_NAME_KEY = 'ack_queue_name'
ACK_ROUTING_KEY = 'ack_routing_key'
ACK_EXCHANGE_NAME_KEY = 'ack_exchange_name'
VIRT_HOST_KEY = 'virtual_host'
USER_NAME_KEY = 'username'
PASSWORD_KEY = 'password'
CLUSTER_ID_KEY = 'cluster_id'


def gen_key(cluster_id, service_name):
    # Generate key for decryption
    key = Cipher.generate_key(cluster_id, service_name)
    return key


def decrypt(key, text):
    '''Decrypt the <text>'''
    decrypt_text = text
    try:
        decrypt_text = Cipher.decrypt(key, text).decode()
        return decrypt_text
    except CipherInvalidToken as e:
        print("Password decryption failed requested by %s" % SECTION)
        return decrypt_text.decode()


def main(product):
    """Main line for this program."""
    virtual_host = Conf.get(SSPL_CONFIG_INDEX, "%s>%s" %
                            (SECTION, VIRT_HOST_KEY))
    username = Conf.get(SSPL_CONFIG_INDEX, "%s>%s" % (SECTION, USER_NAME_KEY))
    password = Conf.get(SSPL_CONFIG_INDEX, "%s>%s" % (SECTION, PASSWORD_KEY))

    if product in cs_legacy_products:
        primary_rabbitmq_server = Conf.get(SSPL_CONFIG_INDEX,
                                           "%s>%s" % (SECTION, "primary_rabbitmq_host"))
        secondary_rabbitmq_server = Conf.get(SSPL_CONFIG_INDEX,
                                             "%s>%s" % (SECTION, "secondary_rabbitmq_server"))
    _check_rabbitmq_status()
    _start_rabbitmq()

    _create_vhost_if_necessary(virtual_host, product)

    # Decrypt password -----------------------
    cluster_id = Conf.get(GLOBAL_CONFIG_INDEX, "%s>%s" %
                          ("cluster", CLUSTER_ID_KEY))
    # Generate key
    key = gen_key(cluster_id, ServiceTypes.RABBITMQ.value)
    password = decrypt(key, password.encode('ascii'))
    _create_user_if_necessary(username, password, virtual_host, product)

    # create durable/mirrored queues in either single or clustered mode.
    create_mirrored_queues(key)

    if product in cs_legacy_products:
        # Copy the erlang key from primary server to secondary and mirror queues
        if primary_rabbitmq_server in hostnames:
            _set_perms_erlang_key()
            _copy_erlang_key(secondary_rabbitmq_server)
            _create_ha_queues()

        # Cluster the secondary server to the primary
        elif secondary_rabbitmq_server in hostnames:
            _set_perms_erlang_key()
            _cluster_rabbitmq_servers(primary_rabbitmq_server, secondary_rabbitmq_server)


def sync_queue(queue_name):
    """Queues need to be synced when new node joined to the cluster.
    """
    command = f'{RABBITMQCTL} sync_queue -p SSPL {queue_name}'
    _send_command(command)


def create_mirrored_queues(decryption_key):
    print('Creating mirrored queues...')
    # creating actuator-req-queue queue.
    vhost, username, password, exchange_name, queue_name, routing_key = \
        _get_connection_config(INGRESS_CONFIG_SECTION)
    _set_ha_policy(queue_name)
    create_queue(vhost, username, decrypt(decryption_key, password.encode('ascii')), exchange_name,
                 queue_name, routing_key)
    sync_queue(queue_name)

    # creating sensor-queue queue
    vhost, username, password, exchange_name, queue_name, routing_key = \
        _get_connection_config(EGRESS_CONFIG_SECTION)
    _set_ha_policy(queue_name)
    create_queue(vhost, username, decrypt(decryption_key, password.encode('ascii')), exchange_name,
                 queue_name, routing_key)
    sync_queue(queue_name)

    # # creating actuator-resp-queue queue
    # vhost, username, password, exchange_name, queue_name, routing_key = \
    #     _get_connection_config(
    #         EGRESS_CONFIG_SECTION,
    #         exchange_key=ACK_QUEUE_NAME_KEY,
    #         queue_key=ACK_QUEUE_NAME_KEY,
    #         routing_key=ACK_ROUTING_KEY
    #     )
    # _set_ha_policy(queue_name)
    # create_queue(vhost, username, decrypt(decryption_key, password.encode('ascii')), exchange_name,
    #              queue_name, routing_key)
    # sync_queue(queue_name)

    # creating iem-queue queue
    vhost, username, password, exchange_name, queue_name, routing_key = \
        _get_connection_config(LOGGER_CONFIG_SECTION)
    _set_ha_policy(queue_name)
    create_queue(vhost, username, decrypt(decryption_key, password.encode('ascii')), exchange_name,
                 queue_name, routing_key)
    sync_queue(queue_name)
    print('Done creating mirrored queues...')


def _set_ha_policy(queue_name):
    print('Setting HA policy for queue {}'.format(queue_name))
    command = f'{RABBITMQCTL} set_policy -p SSPL ha-{queue_name} ' + \
              f'"^{queue_name}$" \'{{"ha-mode":"all"}}\''
    print(command)
    _send_command(command)


def _get_connection_config(section, exchange_key=EXCHANGE_NAME_KEY,
                           queue_key=QUEUE_NAME_KEY, routing_key=ROUTING_KEY):
    vhost = Conf.get(SSPL_CONFIG_INDEX, "%s>%s" % (section, VIRT_HOST_KEY))
    exchange_name = Conf.get(SSPL_CONFIG_INDEX, "%s>%s" %
                             (section, exchange_key))
    queue_name = Conf.get(SSPL_CONFIG_INDEX, "%s>%s" % (section, queue_key))
    routing_key = Conf.get(SSPL_CONFIG_INDEX, "%s>%s" % (section, routing_key))
    username = Conf.get(SSPL_CONFIG_INDEX, "%s>%s" % (section, USER_NAME_KEY))
    password = Conf.get(SSPL_CONFIG_INDEX, "%s>%s" % (section, PASSWORD_KEY))
    return vhost, username, password, exchange_name, queue_name, routing_key


def create_queue(vhost, username, password, exchange_name, queue_name,
                 routing_key):
    creds = pika.PlainCredentials(username, password)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host='localhost',
            credentials=creds,
            virtual_host=vhost,
        )
    )
    channel = connection.channel()
    try:
        channel.queue_declare(queue=queue_name, durable=True)
    except Exception as e:
        print('Exception in queue declaration: {}'.format(e))
    try:
        channel.exchange_declare(
            exchange=exchange_name,
            exchange_type='topic',
            durable=True,
        )
    except Exception as e:
        print('Exception is exchange declaration: {}'.format(e))
    channel.queue_bind(
        queue=queue_name,
        exchange=exchange_name,
        routing_key=routing_key
    )
    connection.close()


def _create_vhost_if_necessary(virtual_host, product):
    """ Creates the specified vhost (if necessary).

    No action will occur if the vhost already exists.

    @type virtual_host:           string
    @param virtual_host:          The vhost to create.
    @type product:                string
    @param product:               The product for which initialization is
                                  being done.
    """
    if product in cs_legacy_products:
        command = "%s list_vhosts" % RABBITMQCTL
        response = _send_command(command, fail_on_error=False)
        # Try restarting service
        if "Error" in response:
            command = "service rabbitmq-server restart"
            _send_command(command)
            command = "%s list_vhosts" % RABBITMQCTL
            response = _send_command(command)

        vhosts = response.split('\n')
        print(f'vhosts: {vhosts}')
        for vhost in vhosts[1:-1]:
            if vhost == virtual_host:
                return

        command = "%s add_vhost %s" % (RABBITMQCTL, virtual_host)
        _send_command(command)
        print("Successfully created vhost: %s" % virtual_host)

    elif product.lower() in [x.lower() for x in enabled_products]:
        vhosts = subprocess.check_output(
            [RABBITMQCTL, 'list_vhosts']
            ).decode("utf-8").split('\n')
        print(f'vhosts: {vhosts}')
        for vhost in vhosts[1:-1]:
            if vhost == virtual_host:
                return
        try:
            subprocess.check_output(
                    f'{RABBITMQCTL} add_vhost {virtual_host}',
                    shell=True, stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode('utf-8')
            print(f'Sub process failed: error: {err_msg}')
            if 'vhost_already_exists' in err_msg:
                print(f'Not creating new virtual host in RabbitMQ')
            else:
                raise
        else:
            print(f'Created new virtual host {virtual_host} in RabbitMQ')
    else:
        raise ValueError("Product should be one of: %s" % (cs_legacy_products + enabled_products))


def _create_user_if_necessary(username, password, virtual_host, product):
    """ Create the rabbitmq user (if necessary).

    The user is created (if it doesn't exist) and then set with .* permissions
    for conf,write,read on the specified virtual_host.

    The permissions will be set regardless of whether or not the user already exists.

    The password will only be set if this is a new user.

    Note: To delete the user, from bash, run::
        rabbitmqctl delete_user <username>

    @type username:               string
    @param username:              The user to create.
    @type password:               string
    @param passowrd:              The password for the specified user.  Will
                                  only be set if this is a new user.
    @type virtual_host:           string
    @param virtual_host:          The vhost on which the permissions will be
                                  set.
    @type product:                string
    @param product:               The product for which initialization is
                                  being done.
    """
    if product in cs_legacy_products:
        command = "%s list_users" % RABBITMQCTL
        response = _send_command(command)

        users = response.split("\n")
        print(f'Users: {users}')
        found_user = False
        for userspec in users[1:-1]:
            user = userspec.split()[0]
            if user == username:
                found_user = True
                break
        if not found_user:
            # Create the user and set permissions, will exit upon error
            command = "%s add_user %s %s" % (RABBITMQCTL, username, password)
            _send_command(command)
            command = "%s set_permissions -p %s %s '.*' '.*' '.*'" % (RABBITMQCTL, virtual_host, username)
            _send_command(command)
            command = "%s set_user_tags %s administrator" % (RABBITMQCTL, username)
            _send_command(command)
    elif product.lower() in [x.lower() for x in enabled_products]:
        users = subprocess.check_output(
            [RABBITMQCTL, 'list_users']
            ).decode("utf-8").split('\n')
        print('Users: {users}')
        found_user = False
        for userspec in users[1:-1]:
            user = userspec.split()[0]
            if user == username:
                found_user = True
                break
        if not found_user:
            try:
                subprocess.check_output(
                        f'{RABBITMQCTL} add_user {username} {password}',
                        shell=True, stderr=subprocess.PIPE
                )
            except subprocess.CalledProcessError as e:
                err_msg = e.stderr.decode('utf-8')
                print(f'Sub process failed: error: {err_msg}')
                if 'user_already_exists' in err_msg:
                    print(f'Not creating new user in RabbitMQ')
                else:
                    raise
            else:
                print(f'Created new user {username} in RabbitMQ')
        subprocess.check_call(
            [
                RABBITMQCTL, 'set_permissions',
                '-p', virtual_host,
                username, '.*', '.*', '.*'
            ])
        subprocess.check_call(
            [RABBITMQCTL, 'set_user_tags', username, 'administrator']
            )
    else:
        raise ValueError("Product should be one of: %s" % (cs_legacy_products + enabled_products))

def _check_rabbitmq_status():
    """Reset if the node is down"""
    command = "service rabbitmq-server status"
    response = _send_command(command, fail_on_error=False)
    if "nodedown" in response:
        print("Nodedown, resetting")
        command = "pkill beam.smp"
        _send_command(command)

def _start_rabbitmq():
    """Ensure rabbitmq-server is started"""
    command = "service rabbitmq-server start"
    _send_command(command)

def _set_perms_erlang_key():
    # Set the ownership and permissions on cluster key
    command = "chown rabbitmq:rabbitmq /var/lib/rabbitmq/.erlang.cookie"
    _send_command(command)
    command = "chmod 400 /var/lib/rabbitmq/.erlang.cookie"
    _send_command(command)

def _copy_erlang_key(secondary_rabbitmq_server):
    """Copy the erlang key from primary server to secondary"""
    # Copy the key from primary server to secondary
    command = "scp /var/lib/rabbitmq/.erlang.cookie root@%s:/var/lib/rabbitmq/.erlang.cookie" % \
                secondary_rabbitmq_server
    response = _send_command(command)
    print("Copy erlang key from primary host to secondary: %s" % response)

def _cluster_rabbitmq_servers(primary_rabbitmq_server, secondary_rabbitmq_server):
    """Perform the steps to cluster the rabbitmq servers"""
    command = "service rabbitmq-server restart"
    response = _send_command(command)
    print("Clustering rabbitmq, restarting server: %s" % response)

    command = "%s stop_app" % RABBITMQCTL
    response = _send_command(command)
    print("Clustering rabbitmq, stopping app: %s" % response)

    command = "nodeattr -v ha_pair | cut -f2 -d:"
    cluster_hostname = _send_command(command)
    print("Joining cluster: %s" % cluster_hostname)

    command = "%s join_cluster rabbit@%s" % \
                (RABBITMQCTL, cluster_hostname)
    response = _send_command(command)
    print("Clustering rabbitmq, joining cluster: %s" % response)

    command = "rabbitmqctl start_app"
    response = _send_command(command)
    print("Clustering rabbitmq, starting: %s" % response)

    # Print the status of the cluster
    command = "rabbitmqctl cluster_status"
    response = _send_command(command)
    print("Clustering rabbitmq, status: %s" % response)

def _create_ha_queues():
    """Mirror the ras_* queues between clustered rabbitmq servers"""
    command = "%s set_policy ha-all \"^ras_\" '{\"ha-mode\":\"all\"}'" % RABBITMQCTL
    response = _send_command(command)
    print("Mirroring queues in cluster: %s" % response)

def _send_command(command, fail_on_error=True):
    print(f'Executing: {command}')
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    response, error = process.communicate()
    if process.returncode != 0:
        print("command '%s' failed with error\n%s" % (command, error))
        if fail_on_error:
            sys.exit(1)
        else:
            return str(error)
    return str(response)


if __name__ == '__main__':
    product = sys.argv[1]
    main(product)
