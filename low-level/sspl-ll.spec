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
Requires:   %{product_family}-libsspl_sec = %{version}-%{release}
Requires:   %{product_family}-libsspl_sec-method_none = %{version}-%{release}
Requires:   cortx-py-utils

# Disabling for LDR_R1-non-requirement
# Requires:  zabbix22-agent

%description
Installs SSPL

%prep
%setup -n %{parent_dir}/low-level

%build
# Required to generate RPM targeted for Python3 even when default Python is 2.
%global __python %{__python3}

%clean
[ "${RPM_BUILD_ROOT}" != "/" ] && rm -rf ${RPM_BUILD_ROOT}

%install
# Copy config file and service startup to correct locations
SSPL_BASE=${RPM_BUILD_ROOT}/opt/seagate/%{product_family}/sspl
mkdir -p $SSPL_BASE
mkdir -p ${RPM_BUILD_ROOT}/etc/{systemd/system,dbus-1/system.d,polkit-1/rules.d,sspl-ll/templates/snmp}
cp -afv files/etc ${RPM_BUILD_ROOT}/
cp -afv files/opt/seagate/sspl/conf $SSPL_BASE/
mkdir -p $SSPL_BASE/bin
mkdir -p $SSPL_BASE/extension

# Copy the service into /opt/seagate/%{product_family}/sspl where it will execute from
cp -rp __init__.py $SSPL_BASE
mkdir -p $SSPL_BASE/low-level
cp -rp . $SSPL_BASE/low-level

# Coping independent executable script inside sspl/low-level to easier access core code access.
SSPL_SETUP=$SSPL_BASE/low-level/files/opt/seagate/sspl/setup
cp -p $SSPL_SETUP/generate_resource_health_view/resource_health_view $SSPL_BASE/low-level/
cp -p $SSPL_SETUP/generate_sspl_bundle/sspl_bundle_generate $SSPL_BASE/low-level/
cp -p $SSPL_SETUP/manifest_support_bundle $SSPL_BASE/low-level/
cp -p $SSPL_SETUP/sspl_setup.py $SSPL_BASE/low-level/sspl_setup
cp -p $SSPL_SETUP/consuldump.py $SSPL_BASE/low-level/
cp -p $SSPL_BASE/low-level/solution/lr2/support_bundle/sspl_support_bundle $SSPL_BASE/low-level/

%pre
# take backup of cache folder if exists
mkdir -p /opt/seagate/%{product_family}/backup/%{version}/sspl
[ -f /etc/sspl.conf ] && cp -p /etc/sspl.conf /opt/seagate/%{product_family}/backup/%{version}/sspl/sspl.conf
if [ -d /var/%{product_family}/sspl/data ]; then
    cp -Rp /var/%{product_family}/sspl/data /opt/seagate/%{product_family}/backup/%{version}/sspl/
fi

%post
SSPL_DIR=/opt/seagate/%{product_family}/sspl

[ -d "${SSPL_DIR}" ] && {
    ln -sf $SSPL_DIR/low-level/resource_health_view $SSPL_DIR/bin/resource_health_view
    ln -sf $SSPL_DIR/low-level/sspl_bundle_generate $SSPL_DIR/bin/sspl_bundle_generate
    ln -sf $SSPL_DIR/low-level/manifest_support_bundle $SSPL_DIR/bin/manifest_support_bundle
    ln -sf $SSPL_DIR/low-level/sspl_setup $SSPL_DIR/bin/sspl_setup
    ln -sf $SSPL_DIR/low-level/consuldump.py $SSPL_DIR/bin/consuldump.py
    ln -sf $SSPL_DIR/low-level/resource_health_view /usr/bin/resource_health_view
    ln -sf $SSPL_DIR/low-level/sspl_bundle_generate /usr/bin/sspl_bundle_generate
    ln -sf $SSPL_DIR/low-level/manifest_support_bundle /usr/bin/manifest_support_bundle
    ln -sf $SSPL_DIR/low-level/framework $SSPL_DIR/low-level/solution/lr2/
    ln -sf $SSPL_DIR/low-level/solution $SSPL_DIR/extension/solution
    ln -sf $SSPL_DIR/low-level/sspl_support_bundle $SSPL_DIR/bin/sspl_support_bundle
}

# restore of data & iem folder
[ -d /opt/seagate/%{product_family}/backup/%{version}/sspl ] &&
    cp -Rp /opt/seagate/%{product_family}/backup/%{version}/sspl/* /var/%{product_family}/sspl/

# Copy rsyslog configuration
# [ -f /etc/rsyslog.d/0-iemfwd.conf ] ||
#    cp /opt/seagate/%{product_family}/sspl/low-level/files/etc/rsyslog.d/0-iemfwd.conf /etc/rsyslog.d/0-iemfwd.conf

# [ -f /etc/rsyslog.d/1-ssplfwd.conf ] ||
#    cp /opt/seagate/%{product_family}/sspl/low-level/files/etc/rsyslog.d/1-ssplfwd.conf /etc/rsyslog.d/1-ssplfwd.conf

if [ "$1" == "1" ]; then
    echo "Installation complete. Follow the instructions."
    echo "Run SSPL mini provisioner commands (post_install, prepare, config, init)"
    echo "Start sspl-ll service."
fi

%preun
# Remove configuration in case of uninstall
if [ "$1" == "0" ]; then
    rm -f /var/%{product_family}/sspl/sspl-configured
fi
systemctl stop sspl-ll.service 2> /dev/null || true

%postun
SSPL_DIR=/opt/seagate/%{product_family}/sspl
rm -f /etc/polkit-1/rules.d/sspl-ll_dbus_policy.rules
rm -f /etc/dbus-1/system.d/sspl-ll_dbus_policy.conf
rm -f /usr/bin/resource_health_view /usr/bin/sspl_bundle_generate /usr/bin/manifest_support_bundle
rm -f $SSPL_DIR/extension/solution

%files
%defattr(-,root,root,-)
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
