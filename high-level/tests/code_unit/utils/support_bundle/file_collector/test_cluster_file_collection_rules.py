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

import unittest
from sspl_hl.utils.support_bundle.file_collector.\
    cluster_files_collection_rules import ClusterFilesCollectionRules


class TestFileCollectionRules(unittest.TestCase):

    def setUp(self):
        self.nodes = ['vmc-rekvm-ssu-1-5.xy01.xyratex.com',
                      'vmc-rekvm-ssu-1-6.xy01.xyratex.com',
                      'vmc-rekvm-ssu-1-3.xy01.xyratex.com',
                      'vmc-rekvm-ssu-1-2.xy01.xyratex.com',
                      'vmc-rekvm-ssu-1-4.xy01.xyratex.com']
        self.hostname = 'vmc-rekvm-cc1.xy01.xyratex.com'
        self.bucket = '2017-05-25_09-45-54'
        self.remote_action_rules = [
            'm0reportbug',
            'mv -f m0reportbug-data.tar.gz /tmp/bundle/',
            'mv -f m0reportbug-traces.tar.gz /tmp/bundle/',
            'mv -f m0reportbug-cores.tar.gz /tmp/bundle/',
            'dmesg > /tmp/bundle/dmesg.log'
        ]
        self.local_action_rules = [
            'm0reportbug',
            'mv -f m0reportbug-data.tar.gz /tmp/bundle/',
            'mv -f m0reportbug-traces.tar.gz /tmp/bundle/',
            'mv -f m0reportbug-cores.tar.gz /tmp/bundle/',
            'dmesg > /tmp/bundle/dmesg.log',
            'echo "Decision Logs could not be collected"'
        ]

        self.fc_rules = ClusterFilesCollectionRules(
            self.nodes, self.hostname, self.hostname)

    def test_keys(self):
        items = self.fc_rules._collection_rules.keys()
        self.assertEquals(items, ['local', 'remote'])

    def test_remote_collection_rule_func(self):
        remote_items = self.fc_rules.get_remote_files_info()
        self.assertIsInstance(remote_items, dict)

    def test_local_collection_rule_func(self):
        local_items = self.fc_rules.get_remote_files_info()
        self.assertIsInstance(local_items, dict)

    def test_check_remote_nodes_attributes(self):
        remote_items = self.fc_rules.get_remote_files_info()
        self.assertEquals(self.nodes.sort(), remote_items.keys().sort())

    def test_remote_rules_action_attrib(self):
        remote_items = self.fc_rules.get_remote_files_info()
        self.assertEquals(
            remote_items.get('vmc-rekvm-ssu-1-3.xy01.xyratex.com').get(
                'action'),
            self.remote_action_rules)

    def test_local_rules_action_attrib(self):
        local_items = self.fc_rules.get_local_files_info()
        self.assertEquals(
            local_items.get('action').sort(), self.local_action_rules.sort())

    def test_remote_rules_structure(self):
        remote_items = self.fc_rules.get_remote_files_info()
        remote_keys = ['action', 'files', 'hosts', 'cleanup', 'bucket']
        self.assertEquals(remote_items.get(
            'vmc-rekvm-ssu-1-3.xy01.xyratex.com').keys().sort(),
            remote_keys.sort())

    def test_local_rules_structure(self):
        local_items = self.fc_rules.get_local_files_info()
        keys = ['action', 'files', 'misc', 'cleanup', 'bucket']
        self.assertEquals(local_items.keys().sort(), keys.sort())


if __name__ == '__main__':
    unittest.main()
