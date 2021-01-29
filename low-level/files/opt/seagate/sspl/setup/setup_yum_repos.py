#!/usr/bin/python3.6

# Copyright (c) 2018-2020 Seagate Technology LLC and/or its Affiliates
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


# *********************************************************
#  Description:   Add common and sspl repos to yum.repos.d
# *********************************************************

import os
import shutil
import argparse
import subprocess

CORTX_BASE_URL = "http://cortx-storage.colo.seagate.com/releases/cortx"

COMMON_REPOS = """[cortx_commons]
name=cortx_commons
gpgcheck=0
enabled=1
baseurl=%s
"""

PLATFORM_BASE = """[cortx_platform_base]
name=cortx_platform_base
gpgcheck=0
enabled=1
baseurl=%s
"""

PLATFORM_EXTRAS = """[cortx_platform_extras]
name=cortx_platform_extras
gpgcheck=0
enabled=1
baseurl=%s
"""

EPEL = """[epel]
name=epel
gpgcheck=0
enabled=1
baseurl=%s
"""

SSPL = """[sspl]
name=sspl
gpgcheck=1
gpgkey=%s
enabled=1
baseurl=%s
"""
SSPL_UPLOADS = """[sspl_uploads]
name=sspl_uploads
gpgcheck=0
enabled=1
baseurl=%s
"""

class SetupYumRepo:

    """Create repo files under /etc/yum.repos.d"""

    name = "Setup Yum Repo"

    def __init__(self, target_build_url):
        """Initialize yum repo object."""
        self.build_url = target_build_url
        self.cortx_deps_repo = None
        self.epel_repo = None
        self.url_sspl_repo = None
        self.url_uploads_repo = None
        self.cortx_commons_repo = "/etc/yum.repos.d/cortx_commons.repo"
        self.cortx_platform_base_repo = "/etc/yum.repos.d/cortx_platform_base.repo"
        self.cortx_platform_extras_repo = "/etc/yum.repos.d/cortx_platform_extras.repo"
        self.third_party_epel_repo = "/etc/yum.repos.d/3rd_party_epel.repo"
        self.sspl_repo = "/etc/yum.repos.d/sspl.repo"
        self.sspl_uploads_repo = "/etc/yum.repos.d/sspl_uploads.repo"

    def _validate_centos_release_support(self):
        """Get CORTX url based on centos release."""
        file = "/etc/centos-release"
        with open(file) as fObj:
            content = fObj.read()
        if "CentOS Linux release 7.8" in content:
            self.url_local_repo_commons="%s/third-party-deps/centos/centos-7.8.2003/" % (CORTX_BASE_URL)
            self.url_uploads_repo = "%s/uploads/centos/centos-7.8.2003/" % (CORTX_BASE_URL)
        elif "CentOS Linux release 7.7" in content:
            self.url_local_repo_commons="%s/third-party-deps/centos/centos-7.7.1908/" % (CORTX_BASE_URL)
            self.url_uploads_repo="%s/uploads/centos/centos-7.7.1908/" % (CORTX_BASE_URL)
        else:
            raise Exception("%s: %s" % (self.name,
                                        "OS version not supported. " +
                                        "Supported OS versions are CentOS-7.7 and CentOS-7.8"))

    def set_repo_url(self):
        """Make build specific url."""
        if self.build_url:
            self.cortx_deps_repo = "%s/3rd_party" % self.build_url
            self.epel_repo = "%s/EPEL-7" % self.build_url
            self.url_local_repo_commons = self.cortx_deps_repo
            self.url_sspl_repo = "%s/cortx_iso" % self.build_url
        self._validate_centos_release_support()

    def create_commons_repos(self):
        """Create common platform base, extra and epel repos."""
        # Create common repo
        content =  COMMON_REPOS % (self.url_local_repo_commons)
        with open(self.cortx_commons_repo, "w") as fObj:
            fObj.write(content)

        # Create platform base repo
        url = ""
        if not self.build_url:
            url = "http://ssc-satellite1.colo.seagate.com/pulp/repos/EOS/Library/custom/CentOS-7/CentOS-7-OS/"

        if url:
            content = PLATFORM_BASE % (url)
            with open(self.cortx_platform_base_repo, "w") as fObj:
                fObj.write(content)

        # Create platform extra repo
        url = ""
        if not self.build_url:
            url = "http://ssc-satellite1.colo.seagate.com/pulp/repos/EOS/Library/custom/CentOS-7/CentOS-7-Extras/"

        if url:
            content = PLATFORM_EXTRAS % (url)
            with open(self.cortx_platform_extras_repo, "w") as fObj:
                fObj.write(content)

        # Create 3rd party epel repo
        url = self.epel_repo
        if not self.build_url:
            url = "http://ssc-satellite1.colo.seagate.com/pulp/repos/EOS/Library/custom/EPEL-7/EPEL-7/"
        content = EPEL % (url)
        with open(self.third_party_epel_repo, "w") as fObj:
            fObj.write(content)

    def create_sspl_repo(self):
        """Create sspl repo file."""
        gpg_file = self.url_sspl_repo + "/RPM-GPG-KEY-Seagate"
        content = SSPL % (gpg_file, self.url_sspl_repo)
        with open(self.sspl_repo, "w") as fObj:
            fObj.write(content)

    def create_sspl_uploads_repo(self):
        """Create sspl uploads repo file."""
        content = SSPL_UPLOADS % (self.url_uploads_repo)
        with open(self.sspl_uploads_repo, "w") as fObj:
            fObj.write(content)

    @staticmethod
    def take_backup(src, dst):
        """Copy files from soruce directory to destination directory."""
        if not os.path.exists(dst):
            os.makedirs(dst)
        for item in os.listdir(src):
            sfile = os.path.join(src, item)
            if os.path.isfile(sfile):
                shutil.copy(sfile, dst)


def main(target_build_url=None):
    """Main method to create yum repo files."""
    yum = SetupYumRepo(target_build_url)

    # Take backup on existing repo
    source_dir = "/etc/yum.repos.d"
    backup_dir = "/etc/yum.repos.d.bkp"
    yum.take_backup(source_dir, backup_dir)

    # Create yum repo files
    yum.set_repo_url()
    yum.create_commons_repos()
    if target_build_url:
        yum.create_sspl_repo()
    yum.create_sspl_uploads_repo()

    # yum cleanup
    cmd1 = "yum autoremove -y"
    cmd2 = "yum clean all"
    subprocess.call(cmd1.split(), stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, shell=False)
    subprocess.call(cmd2.split(), stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, shell=False)

    print("INFO: Created yum repo files.")


if __name__ == '__main__':
    description = "setup_yum_repos"
    argParser = argparse.ArgumentParser(
        formatter_class = argparse.RawDescriptionHelpFormatter, description=description,
        add_help=True, allow_abbrev=False)
    argParser.add_argument("-t", "--target_build_url", default="", help="Target build URL")
    args = argParser.parse_args()
    target_build_url = args.target_build_url
    if target_build_url:
        main(target_build_url)
    else:
        main()
