#xyr build defines
# This section will be re-written by Jenkins build system.
%define _xyr_package_name     SSPL-LL
%define _xyr_package_source   sspl-1.0.0.tgz
%define _xyr_package_version  1.0.0
%define _xyr_build_number     10.el7
%define _xyr_pkg_url          http://es-gerrit:8080/sspl
%define _xyr_svn_version      0
#xyr end defines

Name:       %{_xyr_package_name}
Version:    %{_xyr_package_version}
Release:    %{_xyr_build_number}
Summary:    Installs SSPL-LL
BuildArch:  noarch
Group:      System Environment/Daemons
License:    Seagate Proprietary
URL:        %{_xyr_pkg_url}
Source0:    %{_xyr_package_source}
BuildRoot:  %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildRequires: rpm-build
Requires:   python-daemon python-inotify python-jsonschema python-pika rabbitmq-server
Requires:   python-zope-interface python-zope-event python-zope-component
Requires:   systemd-python pygobject2 dbus
Requires(pre): shadow-utils

%description
Installs SSPL-LL


%pre
getent passwd sspl-ll >/dev/null || \
     useradd -r -g zabbix -G systemd-journal -s /sbin/nologin \
     -c "User account to run the sspl-ll service" sspl-ll


%prep
%setup -n sspl/low-level

%build


%install
# Copy config file and service startup to correct locations
mkdir -p %{buildroot}/etc/systemd/system
mkdir -p %{buildroot}/etc/dbus-1/system.d

cp files/sspl-ll.service %{buildroot}/etc/systemd/system
cp files/sspl_ll.conf %{buildroot}/etc
cp files/sspl-ll_dbus_policy.conf %{buildroot}/etc/dbus-1/system.d

# Copy the service into /opt/seagate/sspl where it will execute from
mkdir -p %{buildroot}/opt/seagate/sspl/low-level
cp -rp . %{buildroot}/opt/seagate/sspl/low-level


%post

# Enable persistent boot information for journald
mkdir -p /var/log/journal
systemctl restart systemd-journald

# Have systemd reload
systemctl daemon-reload

# Enable service to start at boot
systemctl enable sspl-ll

%clean
rm -rf %{buildroot}


%files
%defattr(-,sspl-ll,root,-)
/opt/seagate/sspl/*
%defattr(-,root,root,-)
/etc/systemd/system/sspl-ll.service
/etc/sspl_ll.conf
/etc/dbus-1/system.d/sspl-ll_dbus_policy.conf


%changelog
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
