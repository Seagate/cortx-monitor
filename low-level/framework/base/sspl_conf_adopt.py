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

from configparser import ConfigParser

class ConfDiff(object):

    def __init__(self, conf_file1, conf_file2):
        self.conf_file1_dict = self._to_dict(conf_file1)
        self.conf_file2_dict = self._to_dict(conf_file2)

    def _to_dict(self, file_name):
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

if __name__ == '__main__':
    print('comparing conf files.')
    conf_diff = ConfDiff('/opt/seagate/cortx/sspl/conf/sspl.conf.LDR_R1', '/etc/sspl.conf')
    print('writing destination conf file to tmp dir.')
    conf_diff.update_sub_section_diff()
    with open('/tmp/sspl_tmp.conf', 'w') as configfile:
        conf_diff.conf_file2_dict.write(configfile, space_around_delimiters=False)
