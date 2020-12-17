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

%define _unpackaged_files_terminate_build 0
%define _binaries_in_noarch_packages_terminate_build   0

# build number
%define build_num  %( test -n "$build_number" && echo "$build_number" || echo 1 )

Name:       %{product_family}-sspl
Version:    %{version}
Provides:   %{name} = %{version}
Obsoletes:  %{name} <= %{version}
Release:    %{build_num}_git%{git_rev}%{?dist}
Summary:    Installs SSPL
BuildArch:  noarch
Group:      System Environment/Daemons
License:    Seagate
URL:        https://github.com/Seagate/cortx-sspl
Source0:    %{name}-%{version}.tgz
BuildRoot:  %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildRequires: python36 rpm-build sudo
Requires:   rabbitmq-server udisks2 hdparm python36 ipmitool smartmontools lshw
Requires:   %{product_family}-libsspl_sec = %{version}-%{release}
Requires:   %{product_family}-libsspl_sec-method_none = %{version}-%{release}

#Requires:  python36-dbus python36-paramiko
#Requires:  python36-psutil python36-gobject systemd-python36
Requires:   perl(Config::Any) cortx-py-utils
Requires(pre): shadow-utils

# Disabling for LDR_R1-non-requirement
# Requires:  zabbix22-agent

%description
Installs SSPL

%prep
%setup -n sspl

%build
# Required to generate RPM targeted for Python3 even when default Python is 2.
%global __python %{__python3}

%clean
[ "${RPM_BUILD_ROOT}" != "/" ] && rm -rf ${RPM_BUILD_ROOT}

%install
# Copy config file and service startup to correct locations
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/%{product_family}/sspl
cp -rp . ${RPM_BUILD_ROOT}/opt/seagate/%{product_family}/sspl

%pre
# Add the sspl-ll user during first install if it doesnt exist
# Add this user in the primary group itself instead of zabbix group
id -u sspl-ll &>/dev/null || {
    echo "Creating sspl-ll user..."
    #/usr/sbin/useradd -r -g zabbix -s /sbin/nologin  \
    /usr/sbin/useradd -r sspl-ll -s /sbin/nologin  \
            -c "User account to run the sspl-ll service"
}

# take backup of cache folder if exists
mkdir -p /opt/seagate/backup/%{version}
[ -f /etc/sspl.conf ] && cp -p /etc/sspl.conf /opt/seagate/backup/%{version}/sspl.conf
[ -d /var/%{product_family}/sspl ] && cp -Rp /var/%{product_family}/sspl /opt/seagate/backup/%{version}/

# Create ras persistent cache folder
# TODO: In production this directory will be created by provisioner
# Remove this code when provisioner part is ready.
mkdir -p /var/%{product_family}/sspl/data/
chown -R sspl-ll /var/%{product_family}/sspl/

# Create state file and grant required permission
# This state file will be used later by SSPL resourse agent(HA)
STATE_FILE=/var/%{product_family}/sspl/data/state.txt
[ -f $STATE_FILE ] || touch $STATE_FILE
chown sspl-ll:sspl-ll $STATE_FILE
chmod 644 $STATE_FILE

%post
mkdir -p /var/%{product_family}/sspl/bundle /var/log/%{product_family}/sspl /etc/sspl
SSPL_DIR=/opt/seagate/%{product_family}/sspl
CFG_DIR=$SSPL_DIR/conf

[ -d "${SSPL_DIR}/lib" ] && {
    ln -sf $SSPL_DIR/lib/sspl_ll_d /usr/bin/sspl_ll_d
    ln -sf $SSPL_DIR/lib/resource_health_view /usr/bin/resource_health_view
    ln -sf $SSPL_DIR/lib/sspl_ll_d $SSPL_DIR/bin/sspl_ll_d
    ln -sf $SSPL_DIR/lib/sspl_bundle_generate $SSPL_DIR/bin/sspl_bundle_generate
}

# run conf_diff.py script
[ -f /opt/seagate/%{product_family}/sspl/bin/sspl_conf_adopt.py ] && python3 /opt/seagate/%{product_family}/sspl/bin/sspl_conf_adopt.py

# restore /tmp/sspl_tmp.conf (its updated from previuos version of /etc/sspl.conf & new keys added in sspl.conf.LDR_R1)
[ -f /tmp/sspl_tmp.conf ] && cp /tmp/sspl_tmp.conf /etc/sspl.conf

# restore of data & iem folder
[ -d /opt/seagate/backup/%{version}/sspl ] && cp -Rp /opt/seagate/backup/%{version}/sspl/* /var/%{product_family}/sspl/

# Copy rsyslog configuration
# [ -f /etc/rsyslog.d/0-iemfwd.conf ] ||
#    cp /opt/seagate/%{product_family}/sspl/low-level/files/etc/rsyslog.d/0-iemfwd.conf /etc/rsyslog.d/0-iemfwd.conf

# [ -f /etc/rsyslog.d/1-ssplfwd.conf ] ||
#    cp /opt/seagate/%{product_family}/sspl/low-level/files/etc/rsyslog.d/1-ssplfwd.conf /etc/rsyslog.d/1-ssplfwd.conf

# Copy init script
[ -f /opt/seagate/%{product_family}/sspl/sspl_init ] ||
    ln -s $SSPL_DIR/bin/sspl_provisioner_init /opt/seagate/%{product_family}/sspl/sspl_init

# In case of upgrade start sspl-ll after upgrade
if [ "$1" == "2" ]; then
    echo "Restarting sspl-ll service..."
    systemctl restart sspl-ll.service 2> /dev/null
fi

if [ "$1" = "1" ]; then
    echo "Installation complete. Follow the instructions."
    echo "Run pip3.6 install -r /opt/seagate/%{product_family}/sspl/conf/requirements.txt"
    echo "Run /opt/seagate/%{product_family}/sspl/sspl_init to configure SSPL"
fi

%preun
# Remove configuration in case of uninstall
[[ $1 = 0 ]] &&  rm -f /var/%{product_family}/sspl/sspl-configured
systemctl stop sspl-ll.service 2> /dev/null

%postun
rm -f /etc/polkit-1/rules.d/sspl-ll_dbus_policy.rules
rm -f /etc/dbus-1/system.d/sspl-ll_dbus_policy.conf
[ "$1" == "0" ] && rm -f /opt/seagate/%{product_family}/sspl/sspl_init

%files
%defattr(-,sspl-ll,root,-)
/opt/seagate/%{product_family}/sspl/*

%changelog
* Fri Aug 10 2018 Ujjwal Lanjewar <ujjwal.lanjewar@seagate.com>
- Added version infrastructure and upgrade support

* Wed Oct 18 2017 Oleg Gut <oleg.gut@seagate.com>
- Reworking spec

* Tue Jun 09 2015 Aden Jake Abernathy <aden.j.abernathy@seagate.com>
- Linking into security libraries to apply authentication signatures

* Mon Jun 01 2015 David Adair <dadair@seagate.com>
- Add jenkins-friendly template.  Convert to single tarball for all of sspl.

* Fri May 29 2015 Aden jake Abernathy <aden.j.abernathy@seagate.com> - 1.0.0-9
- Adding request actuator for journald logging, updating systemd unit file
- Adding enabling and disabling of services, moving rabbitmq init script to unit file

* Fri May 01 2015 Aden jake Abernathy <aden.j.abernathy@seagate.com> - 1.0.0-8
- Adding service watchdog module

* Fri Apr 24 2015 Aden jake Abernathy <aden.j.abernathy@seagate.com> - 1.0.0-7
- Updating to run sspl-ll service as sspl-ll user instead of root

* Fri Feb 13 2015 Aden Jake Abernathy <aden.j.abernathy@seagate.com> - 1.0.0-1
- Initial spec file
