Name:       SSPL-LL
Version:    1.0.0
Release:    7.el7
Summary:    Installs SSPL-LL
BuildArch:  noarch
Group:      System Environment/Daemons
License:    Seagate internal company use only
Source0:    sspl-ll.tgz
Source1:    sspl-ll.service
Source2:    sspl_ll.conf
Source3:    sspl-ll_dbus_policy.conf
BuildRoot:  %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildRequires: rpm-build
Requires:   python-daemon python-inotify python-jsonschema python-pika rabbitmq-server
Requires:   python-zope-interface python-zope-event python-zope-component
Requires:	systemd-python
Requires(pre): shadow-utils

%description
Installs SSPL-LL


%pre
getent passwd sspl-ll >/dev/null || \
     useradd -r -g zabbix -s /sbin/nologin \
     -c "User account to run the sspl-ll service" sspl-ll


%prep
cp %SOURCE0 .
cp %SOURCE1 .
cp %SOURCE2 .
cp %SOURCE3 .


%build


%install
# Copy config file and service startup to correct locations
mkdir -p %{buildroot}/etc/init.d
cp sspl-ll.service %{buildroot}/etc/systemd/system
cp sspl_ll.conf %{buildroot}/etc
cp sspl-ll_dbus_policy.conf %{buildroot}/etc/dbus-1/system.d

# Untar the service into /opt/seagate/sspl where it will execute from
mkdir -p %{buildroot}/opt/seagate/sspl
tar zxvf sspl-ll.tgz --directory %{buildroot}/opt/seagate/sspl


%post
# setup rabbitmq vhost and user (incl permissions)
/opt/seagate/sspl/low-level/framework/sspl_ll_rabbitmq_reinit

# Have systemd reload
systemctl daemon-reload

%clean
rm -rf %{buildroot}


%files
%defattr(-,sspl-ll,sspl-ll,-)
/opt/seagate/sspl/*
%defattr(-,root,root,-)
/etc/systemd/system/sspl-ll.service
/etc/sspl_ll.conf
/etc/dbus-1/system.d/sspl-ll_dbus_policy.conf


%changelog
* Fri Apr 24 2015 Aden jake Abernathy <aden.j.abernathy@seagate.com> - 1.0.0-7
- Updating to run sspl-ll service as sspl-ll user instead of root

* Fri Feb 13 2015 Aden Jake Abernathy <aden.j.abernathy@seagate.com> - 1.0.0-1
- Initial spec file
