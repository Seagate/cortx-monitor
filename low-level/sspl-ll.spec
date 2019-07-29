%define name sspl
%define url  http://gerrit.mero.colo.seagate.com:8080/#/admin/projects/sspl

%define _unpackaged_files_terminate_build 0
%define _binaries_in_noarch_packages_terminate_build   0

Name:       %{name}
Version:    %{version}
Provides:   %{name} = %{version}
Obsoletes:  %{name} <= %{version}
Release:    %{dist}
Summary:    Installs SSPL
BuildArch:  noarch
Group:      System Environment/Daemons
License:    Seagate Proprietary
URL:        %{url}/%{name}
Source0:    %{name}-%{version}.tgz
BuildRoot:  %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildRequires: rpm-build sudo python-Levenshtein
Requires:   python-daemon python-zope-interface python-zope-event python-zope-component python-pika python-jsonschema rabbitmq-server
Requires:   pysnmp systemd-python pygobject2 python-slip-dbus udisks2 python-psutil python-inotify python-paramiko hdparm pyserial
Requires:   python-requests
Requires:   libsspl_sec libsspl_sec-method_none
Requires:   perl(Config::Any)
Requires(pre): shadow-utils

# Disabling for EES-non-requirement
# Requires:  zabbix22-agent

%description
Installs SSPL

%prep
%setup -n sspl/low-level

%build

%clean
[ "${RPM_BUILD_ROOT}" != "/" ] && rm -rf ${RPM_BUILD_ROOT}

%install
# Copy config file and service startup to correct locations
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/sspl
mkdir -p ${RPM_BUILD_ROOT}/etc/{systemd/system,dbus-1/system.d,polkit-1/rules.d,sspl-ll/templates/snmp}
cp -afv files/etc ${RPM_BUILD_ROOT}/
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/sspl/conf
cp -afv files/opt ${RPM_BUILD_ROOT}/

# Copy the service into /opt/seagate/sspl where it will execute from
cp -rp __init__.py ${RPM_BUILD_ROOT}/opt/seagate/sspl
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/sspl/low-level
cp -rp . ${RPM_BUILD_ROOT}/opt/seagate/sspl/low-level

%pre
# Add the sspl-ll user during first install if it doesnt exist
# Add this user in the primary group itself instead of zabbix group
id -u sspl-ll &>/dev/null || {
    echo "Creating sspl-ll user..."
    #/usr/sbin/useradd -r -g zabbix -s /sbin/nologin  \
    /usr/sbin/useradd -r sspl-ll -s /sbin/nologin  \
            -c "User account to run the sspl-ll service"
}

# Create ras persistent cache folder
# TODO: In production this directory will be created by provisioner
# Remove this code when provisioner part is ready.
mkdir -p /var/sspl/data/
chown -R sspl-ll /var/sspl/

%post
# NOTE: By default the sspl default conf file will not be copied.
# The provisioner is supposed to copy the appropriate conf file based
# on product/env and start SSPL with it.
# TODO: Disable this default copy once the provisioners are ready.
[ -f /etc/sspl.conf ] || cp /opt/seagate/sspl/conf/sspl.conf.EES /etc/sspl.conf

# Copy init script
[ -f /opt/seagate/sspl/sspl_init ] ||
    ln -s /opt/seagate/sspl/low-level/framework/sspl_init /opt/seagate/sspl/sspl_init

# In case of upgrade start sspl-ll after upgrade
if [ "$1" == "2" ]; then
    echo "Restarting sspl-ll service..."
    systemctl restart sspl-ll.service 2> /dev/null
fi

mkdir -p /var/log/journal
systemctl restart systemd-journald

# Have systemd reload
systemctl daemon-reload

if [ "$1" = "1" ]; then
    # Enable services to start at boot
    systemctl enable rabbitmq-server
    echo "Installation complete !! Run /opt/seagate/sspl/sspl_init to configure SSPL"
fi

%preun
# Remove configuration in case of uninstall
[[ $1 = 0 ]] &&  rm -f /var/sspl/sspl-configured
systemctl stop sspl-ll.service 2> /dev/null

%postun
rm -f /etc/polkit-1/rules.d/sspl-ll_dbus_policy.rules
rm -f /etc/dbus-1/system.d/sspl-ll_dbus_policy.conf
[ "$1" == "0" ] && rm -f /opt/seagate/sspl/sspl_init

%files
%defattr(-,sspl-ll,root,-)
/opt/seagate/sspl/__init__.py
/opt/seagate/sspl/low-level
/opt/seagate/sspl/conf/sspl.conf.sample
/opt/seagate/sspl/conf/sspl.conf.gw
/opt/seagate/sspl/conf/sspl.conf.ssu
/opt/seagate/sspl/conf/sspl.conf.EES
/opt/seagate/sspl/conf/sspl-ll.service.EES
/opt/seagate/sspl/conf/sspl-ll.service.sample

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
