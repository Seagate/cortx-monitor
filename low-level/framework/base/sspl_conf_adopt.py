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

import os
import yaml
from configparser import ConfigParser

class IniConfDiff(object):
    """Update ini config difference in bakcup config file"""

    def __init__(self, conf_file1, conf_file2):
        self.conf_file1_dict = self._to_dict(conf_file1)
        self.conf_file2_dict = self._to_dict(conf_file2)

    def _to_dict(self, file_name):
        """Convert ini file to dict"""
        config = ConfigParser()
        config.read(file_name)
        return config

    def update_sub_section_diff(self):
        conf_file1_section = self.conf_file1_dict._sections
        conf_file2_section = self.conf_file2_dict._sections
        for item in set(conf_file1_section):
            if conf_file2_section.get(item):
                diff = {k: conf_file1_section[item][k] for k in set(conf_file1_section[item]) - set(conf_file2_section[item])}
                if diff:
                    conf_file2_section[item].update(diff)
            else:
                conf_file2_section[item] = conf_file1_section[item]


class YamlConfDiff(object):
    """Update yaml config difference in bakcup config file"""

    def __init__(self, conf_file1, conf_file2):
        self.conf_file1_dict = self._to_dict(conf_file1)
        self.conf_file2_dict = self._to_dict(conf_file2)

    def _to_dict(self, file1):
        """Convert yaml file to dict"""
        config = yaml.safe_load(open(file1))
        return config

    def update_diff(self, d1, d2):
        for k in d1:
            if not d2.get(k):
                d2.update({k: dict()})
            if type(d1[k]) is list:
                d2[k] = d1[k]
            elif type(d1[k]) is dict and type(d2[k]) is dict:
                v1 = d1[k]
                v2 = d2[k]
                self.update_diff(v1, v2)
            else:
                if d1[k] != d2[k]:
                    d2[k] = d1[k]

if __name__ == '__main__':
    config_file1 = '/opt/seagate/cortx/sspl/conf/sspl.conf.LR2.yaml'
    config_file2 = '/etc/sspl.conf'
    tmp_config_file = '/tmp/sspl_tmp.conf'
    file_type = "yaml"
    print('comparing conf files.')
    if os.path.exists(config_file1) and os.path.exists(config_file2):
        if file_type == "ini":
            conf_diff = IniConfDiff(config_file1, config_file2)
            print('writing destination conf file to tmp dir.')
            conf_diff.update_sub_section_diff()
            with open(tmp_config_file, 'w') as configfile:
                conf_diff.conf_file2_dict.write(configfile, space_around_delimiters=False)
        elif file_type == "yaml":
            conf_diff = YamlConfDiff(config_file1, config_file2)
            print('writing destination conf file to tmp dir.')
            conf_diff.update_diff(conf_diff.conf_file1_dict,
                                conf_diff.conf_file2_dict)
            json_to_yaml = yaml.dump(conf_diff.conf_file2_dict)
            with open(tmp_config_file, 'w') as configfile:
                configfile.write(json_to_yaml)
            with open(config_file2, 'w') as configfile:
                configfile.write(json_to_yaml)
        else:
            print("Unknown config file type.")
