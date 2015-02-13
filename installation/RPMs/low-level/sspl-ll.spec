Name:       SSPL-LL
Version:    1.0.0
Release:    1.el7
Summary:    Installs SSPL-LL
BuildArch:  noarch
Group:      System Environment/Daemons
License:    Seagate internal company use only
Source0:    sspl-ll.tgz
Source1:    sspl-ll
Source2:    sspl_ll.conf
BuildRoot:  %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildRequires: rpm-build
Requires:   python-daemon python-inotify python-jsonschema python-pika rabbitmq-server python-twisted-core

%description
Installs SSPL-LL


%prep
cp %SOURCE0 .
cp %SOURCE1 .
cp %SOURCE2 .


%build


%install
# Copy config file and service startup to correct locations
mkdir -p %{buildroot}/etc/init.d
cp sspl-ll %{buildroot}/etc/init.d
cp sspl_ll.conf %{buildroot}/etc

# Untar the service into /opt/seagate/sspl where it will execute from
mkdir -p %{buildroot}/opt/seagate/sspl
tar zxvf sspl-ll.tgz --directory %{buildroot}/opt/seagate/sspl


%post
# Create the drivemanager directory
if [[ ! -d /tmp/dcs/drivemanager ]]; then 
   mkdir -p /tmp/dcs/drivemanager
   chmod 777 /tmp/dcs
   chmod 777 /tmp/dcs/drivemanager
fi

# Have the service startup at boot time
chkconfig sspl-ll on

# Start the service
systemctl start sspl-ll -l


%clean
rm -rf %{buildroot}


%files
%defattr(-,root,root,-)
/opt/seagate/sspl/*
/etc/init.d/sspl-ll
/etc/sspl_ll.conf


%changelog
* Fri Feb 13 2015 Aden Jake Abernathy <aden.j.abernathy@seagate.com> - 1.0.0-1
- Initial spec file
