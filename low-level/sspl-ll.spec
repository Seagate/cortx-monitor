%define _unpackaged_files_terminate_build 0
%define _binaries_in_noarch_packages_terminate_build   0

# build number
%define build_num  %( test -n "$build_number" && echo "$build_number" || echo 1 )

Name:       eos-sspl
Version:    %{version}
Provides:   %{name} = %{version}
Obsoletes:  %{name} <= %{version}
Release:    %{build_num}_git%{git_rev}%{?dist}
Summary:    Installs SSPL
BuildArch:  noarch
Group:      System Environment/Daemons
License:    Seagate Proprietary
URL:        http://gerrit.mero.colo.seagate.com:8080/#/admin/projects/sspl
Source0:    %{name}-%{version}.tgz
BuildRoot:  %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildRequires: python36 rpm-build sudo
Requires:   rabbitmq-server udisks2 hdparm python36 ipmitool eos-libsspl_sec eos-libsspl_sec-method_none
#Requires:  python36-dbus python36-paramiko
#Requires:  python36-psutil python36-gobject systemd-python36
Requires:   perl(Config::Any) eos-py-utils
Requires(pre): shadow-utils

# Disabling for EES-non-requirement
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
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/eos/sspl
cp -rp . ${RPM_BUILD_ROOT}/opt/seagate/eos/sspl

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
[ -f /etc/sspl.conf ] && cp /etc/sspl.conf /opt/seagate/backup/%{version}/sspl.conf
[ -d /var/eos/sspl ] && cp -R /var/eos/sspl /opt/seagate/backup/%{version}/

# Create ras persistent cache folder
# TODO: In production this directory will be created by provisioner
# Remove this code when provisioner part is ready.
mkdir -p /var/eos/sspl/data/
chown -R sspl-ll /var/eos/sspl/

%post
mkdir -p /var/eos/sspl/bundle /var/log/eos/sspl /etc/sspl
SSPL_DIR=/opt/seagate/eos/sspl
CFG_DIR=$SSPL_DIR/conf

[ -d "${SSPL_DIR}/lib" ] && {
    ln -sf $SSPL_DIR/lib/sspl_ll_d /usr/bin/sspl_ll_d
    ln -sf $SSPL_DIR/lib/sspl_ll_cli /usr/bin/sspl_ll_cli
    ln -sf $SSPL_DIR/lib/sspl_ll_d $SSPL_DIR/bin/sspl_ll_d
    ln -sf $SSPL_DIR/lib/sspl_ll_cli $SSPL_DIR/bin/sspl_ll_cli
}

# run conf_diff.py script
[ -f /opt/seagate/eos/sspl/bin/sspl_conf_adopt.py ] && python3 /opt/seagate/eos/sspl/bin/sspl_conf_adopt.py

# restore /tmp/sspl_tmp.conf (its updated from previuos version of /etc/sspl.conf & new keys added in sspl.conf.EES)
[ -f /tmp/sspl_tmp.conf ] && cp /tmp/sspl_tmp.conf /etc/sspl.conf

# restore of data & iem folder
[ -d /opt/seagate/backup/%{version}/sspl ] && cp -R /opt/seagate/backup/%{version}/sspl/* /var/eos/sspl/

# Copy rsyslog configuration
# [ -f /etc/rsyslog.d/0-iemfwd.conf ] ||
#    cp /opt/seagate/eos/sspl/low-level/files/etc/rsyslog.d/0-iemfwd.conf /etc/rsyslog.d/0-iemfwd.conf

# [ -f /etc/rsyslog.d/1-ssplfwd.conf ] ||
#    cp /opt/seagate/eos/sspl/low-level/files/etc/rsyslog.d/1-ssplfwd.conf /etc/rsyslog.d/1-ssplfwd.conf

# Copy init script
[ -f /opt/seagate/eos/sspl/sspl_init ] ||
    ln -s $SSPL_DIR/bin/sspl_provisioner_init /opt/seagate/eos/sspl/sspl_init

# In case of upgrade start sspl-ll after upgrade
if [ "$1" == "2" ]; then
    echo "Restarting sspl-ll service..."
    systemctl restart sspl-ll.service 2> /dev/null
fi

if [ "$1" = "1" ]; then
    echo "Installation complete. Follow the instructions."
    echo "Run pip3.6 install -r /opt/seagate/eos/sspl/conf/requirements.txt"
    echo "Run /opt/seagate/eos/sspl/sspl_init to configure SSPL"
fi

%preun
# Remove configuration in case of uninstall
[[ $1 = 0 ]] &&  rm -f /var/eos/sspl/sspl-configured
systemctl stop sspl-ll.service 2> /dev/null

%postun
rm -f /etc/polkit-1/rules.d/sspl-ll_dbus_policy.rules
rm -f /etc/dbus-1/system.d/sspl-ll_dbus_policy.conf
[ "$1" == "0" ] && rm -f /opt/seagate/eos/sspl/sspl_init

%files
%defattr(-,sspl-ll,root,-)
/opt/seagate/eos/sspl/*

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
