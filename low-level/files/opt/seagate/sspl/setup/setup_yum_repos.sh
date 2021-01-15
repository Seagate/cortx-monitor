#!/bin/bash
#
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.
#


# *********************************************************
#  Description:   Add common and sspl repos to yum.repos.d
#  Purpose    :   To install dependencies and SSPL rpms
#  Usage      :   ./setup_yum_repos.sh --help
# *********************************************************


set -eE

LOG_FILE="${LOG_FILE:-/var/log/cortx/sspl/sspl-prereqs.log}"
export LOG_FILE

echo "***** Running $0 *****"

tmpdir="/tmp/_cortx_sspl_prereqs_"
mkdir -p $tmpdir

tgt_build=
cortx_deps_repo=
epel_repo=
url_sspl_repo=
url_uploads_repo=
cortx_commons_repo="/etc/yum.repos.d/cortx_commons.repo"
cortx_platform_base_repo="/etc/yum.repos.d/cortx_platform_base.repo"
cortx_platform_extras_repo="/etc/yum.repos.d/cortx_platform_extras.repo"
third_party_epel_repo="/etc/yum.repos.d/3rd_party_epel.repo"
sspl_repo="/etc/yum.repos.d/sspl.repo"
sspl_uploads_repo="/etc/yum.repos.d/sspl_uploads.repo"
bundled_release=false
CORTX_BASE_URL="http://cortx-storage.colo.seagate.com/releases/cortx"

# Repo url for sspl, sspl_uploads & in house built commons packages CentOS systems
if grep -q "CentOS Linux release 7.8" /etc/*-release; then
    url_local_repo_commons="$CORTX_BASE_URL/third-party-deps/centos/centos-7.8.2003/"
    url_uploads_repo="$CORTX_BASE_URL/uploads/centos/centos-7.8.2003/"
elif grep -q "CentOS Linux release 7.7" /etc/*-release; then
    url_local_repo_commons="$CORTX_BASE_URL/third-party-deps/centos/centos-7.7.1908/"
    url_uploads_repo="$CORTX_BASE_URL/uploads/centos/centos-7.7.1908/"
fi

# Repo url for in house built commons packages for RHEL systems
url_local_repo_commons_rhel="$CORTX_BASE_URL/third-party-deps/rhel/rhel-7.7.1908/"

# Repo url for in house built HA packages for RHEL systems
#url_local_repo_rhel_ha="$CORTX_BASE_URL/rhel_local_ha/"

# Repo url for Saltstack
# url_saltstack_repo="https://repo.saltstack.com/py3/redhat/$releasever/$basearch/3000"

function trap_handler {
    rm -rf $tmpdir || true
    echo "***** FAILED!! *****"
    echo "For more details see $LOG_FILE"
    exit 2
}

function trap_handler_exit {
    rm -rf $tmpdir || true
    if [[ $? -eq 1 ]]; then
        echo "***** FAILED!! *****"
        echo "For more details see $LOG_FILE"
    else
        exit $?
    fi
}

trap trap_handler ERR
trap trap_handler_exit EXIT

if [[ ! -e "$LOG_FILE" ]]; then
    mkdir -p $(dirname "${LOG_FILE}")
fi

do_reboot=false

usage()
{
    echo "\

    Cortx Prerequisite script.

    Usage:
         $0 [-t|--target-build-url <url>] [-h|--help]

    OPTION:
    -t|--target-build-url   Target build url pointed to release bundle base directory,
                              if specified the following directory structure is assumed:
                              <base_url>/
                                 centos7.7   <- OS ISO is mounted here
                                 3rd_party              <- CORTX 3rd party ISO is mounted here
                                 cortx_iso              <- CORTX ISO (main) is mounted here
    "
    exit 0
}

parse_args()
{
    while [[ $# -gt 0 ]]; do
        case "$1" in
        -h|--help)
            usage
        ;;
        -t|--target-build-url)
            [ -z "$2" ] &&
                echo "ERROR: Target build not provided" && exit 1;
            tgt_build="$2"

            bundled_release=true

            cortx_deps_repo="${tgt_build}/3rd_party"
            epel_repo="${cortx_deps_repo}/EPEL-7"

            #url_saltstack_repo="${cortx_deps_repo}/commons/saltstack-3001"
            url_local_repo_commons_rhel="$cortx_deps_repo"
            url_local_repo_commons="$cortx_deps_repo"

            url_sspl_repo="${tgt_build}/cortx_iso"

            shift 2 ;;
        *)
            echo "ERROR: Unknown option provided: $1"
            exit 1
        esac
    done
}

create_commons_repo_rhel()
{
    _repo_name="$1"
    _url="$2"
    _repo="/etc/yum.repos.d/${_repo_name}.repo"
    echo -ne "\tCreating ${_repo}.................."

cat <<EOF > "${_repo}"
[$_repo_name]
name=$_repo_name
gpgcheck=0
enabled=1
baseurl=$_url
EOF
    echo "Done."

}


create_commons_repos()
{
    cortx_commons_url="${1:-$url_local_repo_commons}"
    local _repo="$cortx_commons_repo"
    local _url="$cortx_commons_url"
    echo -ne "\tCreating ${_repo}................."
cat <<EOL > "${_repo}"
[cortx_commons]
name=cortx_commons
gpgcheck=0
enabled=1
baseurl=$_url
EOL
    echo "Done" | tee -a "${LOG_FILE}"

    local _repo="$cortx_platform_base_repo"
    if [[ "$bundled_release" == true && -z "$LAB_ENV" ]]; then
        local _url=
    else
        local _url="http://ssc-satellite1.colo.seagate.com/pulp/repos/EOS/Library/custom/CentOS-7/CentOS-7-OS/"
    fi

    if [[ -n "$_url" ]]; then
        echo -ne "\tCreating ${_repo}..........."
cat <<EOL > "${_repo}"
[cortx_platform_base]
name=cortx_platform_base
gpgcheck=0
enabled=1
baseurl=$_url
EOL
        echo "Done" | tee -a "${LOG_FILE}"
    fi

    local _repo="$cortx_platform_extras_repo"
    if [[ "$bundled_release" == true && -z "$LAB_ENV" ]]; then
        local _url=
    else
        local _url="http://ssc-satellite1.colo.seagate.com/pulp/repos/EOS/Library/custom/CentOS-7/CentOS-7-Extras/"
    fi

    if [[ -n "$_url" ]]; then
        echo -ne "\tCreating ${_repo}........."
cat <<EOL > "${_repo}"
[cortx_platform_extras]
name=cortx_platform_extras
gpgcheck=0
enabled=1
baseurl=$_url
EOL
        echo "Done" | tee -a "${LOG_FILE}"
    fi

    local _repo="$third_party_epel_repo"
    if [[ "$bundled_release" == true ]]; then
        local _url="$epel_repo"
    else
        local _url="http://ssc-satellite1.colo.seagate.com/pulp/repos/EOS/Library/custom/EPEL-7/EPEL-7/"
    fi
    echo -ne "\tCreating ${_repo}................"
cat <<EOL > "${_repo}"
[epel]
name=epel
gpgcheck=0
enabled=1
baseurl=$_url
EOL

    echo "Done."
}


create_sspl_repo()
{
    cortx_sspl_url="${1:-$url_sspl_repo}"
    local _repo="$sspl_repo"
    local _url="$cortx_sspl_url"
    local _gpg_file="$_url/RPM-GPG-KEY-Seagate"
    echo -ne "\tCreating ${_repo}................."
cat <<EOL > "${_repo}"
[sspl]
name=sspl
gpgcheck=1
gpgkey=$_gpg_file
enabled=1
baseurl=$_url
EOL
    echo "Done" | tee -a "${LOG_FILE}"
}


create_sspl_uploads_repo()
{
    cortx_sspl_uploads_url="${1:-$url_uploads_repo}"
    local _repo="$sspl_uploads_repo"
    local _url="$cortx_sspl_uploads_url"
    echo -ne "\tCreating ${_repo}................."
cat <<EOL > "${_repo}"
[sspl_uploads]
name=sspl_uploads
gpgcheck=0
enabled=1
baseurl=$_url
EOL
    echo "Done" | tee -a "${LOG_FILE}"
}


parse_args "$@"

echo -n "INFO: Checking hostnames............................................."

srvnode_hostname=$(hostname -f)
if [[ "$srvnode_hostname" != *"."* ]]; then
    echo -e "\nERROR: 'hostname -f' did not return the FQDN, please set FQDN and retry."
    exit 1
else
    echo "Done."
fi

echo -n "INFO: Checking if kernel version is correct.........................."

if grep -E -q "Red Hat.*7.7" /etc/*-release; then
    req_kernel_version='3.10.0-1062.el7.x86_64'
elif grep -q "CentOS Linux release 7.7" /etc/*-release; then
    req_kernel_version='3.10.0-1062.el7.x86_64'
elif grep -q "CentOS Linux release 7.8" /etc/*-release; then
    req_kernel_version='3.10.0-1127.el7.x86_64'
else
    echo -e "\nERROR: OS version not supported. Supported OS: RedHat-7.7, CentOS-7.7 and CentOS-7.8"
    exit 1
fi

kernel_version=$(uname -r)
if [[ "$kernel_version" != "$req_kernel_version" ]]; then
    echo -e "\nERROR: Kernel version is not supported. Required: $req_kernel_version installed: $kernel_version"
    exit 1
else
    echo "Done."
fi

echo "INFO: Creating repos for Cotrx"
create_commons_repos "$url_local_repo_commons"
[ -n "$tgt_build" ] && {
    create_sspl_repo "$url_sspl_repo"
}

create_sspl_uploads_repo "$url_uploads_repo"

echo -n "INFO: Cleaning yum cache............................................."
yum autoremove -y >> ${LOG_FILE}
yum clean all >> ${LOG_FILE}
echo "Done." && sleep 1

# Install lspci command
rpm -qa|grep "pciutils-"|grep -qv "pciutils-lib" && {
    echo "INFO: pciutils package is already installed."
} || {
    echo "INFO: Installing pciutils package"
    yum install -y pciutils
}
if ( lspci -d"15b3:*"|grep Mellanox ) ; then
    rpm -qa | grep -q mlnx-ofed-all && rpm -qa | grep -q mlnx-fw-updater && {
        echo "INFO: Mellanox Drivers are already installed."
    } || {
        echo "INFO: Installing Mellanox drivers"
        yum install -y mlnx-ofed-all mlnx-fw-updater
        echo "INFO: Mellanox drivers succcessfully installed. System will be rebooted atlast."
        do_reboot=true
    }
    echo "INFO: Installing sg3_utils"
    yum install -y sg3_utils
    echo "INFO: Scanning SCSI bus............................................" | tee -a "${LOG_FILE}"
    /usr/bin/rescan-scsi-bus.sh -a >> "${LOG_FILE}"
fi

echo -e "INFO: Disabling default time syncronization mechanism..........."
if [ $(rpm -qa chrony) ]; then
    systemctl stop chronyd && systemctl disable chronyd &>> "${LOG_FILE}"
    yum remove -y chrony &>> "${LOG_FILE}"
fi

if [[ "$do_reboot" == true ]]; then
    echo "INFO: Rebooting the system now"
    shutdown -r now
fi
