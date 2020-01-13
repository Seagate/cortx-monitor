from ConfigParser import ConfigParser

class EqualsSpaceRemover:
    output_file = None
    def __init__(self, new_output_file):
        self.output_file = new_output_file

    def write(self, diffgen):
        self.output_file.write(diffgen.replace( " = ", "=", 1 ))

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
            diff = {k: conf_file1_section[item][k] for k in set(conf_file1_section[item]) - set(conf_file2_section[item])}
            if diff:
                conf_file2_section[item].update(diff)

if __name__ == '__main__':
    print('comparing conf files.')
    conf_diff = ConfDiff('/opt/seagate/sspl/conf/sspl.conf.EES', '/etc/sspl.conf')
    print('writing destination conf file to tmp dir.')
    conf_diff.update_sub_section_diff()
    with open('/tmp/sspl_tmp.conf', 'w') as configfile:
        conf_diff.conf_file2_dict.write(EqualsSpaceRemover(configfile))
