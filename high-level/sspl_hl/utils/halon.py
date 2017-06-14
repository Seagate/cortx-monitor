"""This module will handle all the communication/queries/config param
needed for or by Halon interface"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2017 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.
# __author__ = 'Bhupesh Pant'
import json
import urllib2
from plex.core import log as logger
import yaml


class YamlParser(object):
    """Halon yaml file configuration parsing is done here"""

    def __init__(self, config):
        self._file = config
        self._config_data = None
        self.load()

    def load(self):
        """load the config file into the yaml object"""
        try:
            self._config_data = yaml.load(file(self._file, 'r'))
        except OSError:
            pass

    def to_json(self):
        """convert the given yaml to json format"""
        return self._config_data

    def extract(self, attrib):
        """Extract a higher level attribute from the Yaml and return"""
        return self._config_data.get(attrib)


class HalonConfigurationYaml(object):
    """Reads Halon configuration from halon yaml configuration files,
     1. /etc/halon/halon_facts.yaml
     2. /etc/halon/halon_role_mappings
     and returns the specific configuration parameter.
     """

    def __init__(self):
        self.facts_file = '/etc/halon/halon_facts.yaml'
        self.role_mapping_file = '/etc/halon/halon_role_mappings'

    def _search_station_rack_enclosure(self, racks_info):
        """Searches for station rack enclose in the rack_info list"""
        station_info = {}
        for rack in racks_info:
            if len(rack.get('rack_enclosures')) > 1:
                for enc_info in rack.get('rack_enclosures'):
                    enc_hosts = enc_info['enc_hosts'][-1]
                    for role in enc_hosts.get('h_halon').get('roles'):
                        if role.get('name') == 'station':
                            for h_interface in enc_hosts['h_interfaces']:
                                if h_interface.get('if_network') \
                                        == 'Management':
                                    station_info['ip'] = \
                                        h_interface.get('if_ipAddrs')[-1]
                                    station_info['hostname'] = \
                                        enc_hosts.get('h_fqdn')
                                    return station_info

    def _search_logs_path(self, role_info):
        """Look for the station information in the halon_role_mapping yaml
        and extract the log file path/name"""
        for info in role_info:
            if info.get('name') == 'station':
                for service in info.get('h_services'):
                    if 'halon.decision.log' in service:
                        return service.split()[3]

    def get_station_node_info(self):
        """Extract the Station node information from halon_facts.yaml file"""
        try:
            parser = YamlParser(self.facts_file)
        except IOError as err:
            logger.warning('Could not read role_mapping_file.'
                           ' Details: {}'.format(str(err)))
            logger.info('Trying default location: </etc/halon/{}>'.
                        format(self.facts_file))
            return 'DUMMY_FACTS_FILE'

        racks_info = parser.extract('id_racks')
        return self._search_station_rack_enclosure(racks_info).get('ip')

    def get_decision_logs_path(self):
        """Parse the decision logs path information from
        halon_role_mappings file"""
        try:
            parser = YamlParser(self.role_mapping_file)
        except IOError as err:
            logger.warning('Could not read role_mapping_file.'
                           ' Details: {}'.format(str(err)))
            logger.info('Trying default location: </etc/halon/{}>'.
                        format(self.role_mapping_file))
            return '/etc/halon/{}'.format(self.role_mapping_file)

        role_info = parser.to_json()
        return self._search_logs_path(role_info)


class HalonConfigurationPuppet(HalonConfigurationYaml):
    """Provides the Halon Configuration by querying Puppet"""

    def get_station_node_info(self):
        """Get the station node info by querying Puppet"""
        puppet_query = \
            'http://127.0.0.91:8082/v3/nodes/puppet/facts/station_nodes'
        try:
            response = urllib2.urlopen(puppet_query)
        except urllib2.URLError as err:
            logger.warning('The URL for querying puppet for station node'
                           ' info is invalid. Details: {}'.format(str(err)))
            return 'DUMMY_IP'
        try:
            data = json.loads(response.read())
            for node in data:
                if node.get('name') == 'station_nodes':
                    return json.loads(node.get('value'))[-1]
        except (KeyError, TypeError):
            logger.warning('The station node could not be fetched. '
                           'Details: Puppet service cannot be queried.')
            return 'DUMMY_IP'
