Name:		SSPL-LL
Version:	1.0.0
Release:	1.el7
Summary:	Installs SSPL-LL
BuildArch:      noarch
Group:		SSG
License:	Seagate internal company use only
Source0:        sspl-ll.tgz
Source1:        sspl-ll
Source2:        sspl_ll.conf
BuildRoot:	%(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
BuildRequires:	rpm-build
Requires:	python-daemon python-pyinotify python-jsonschema

%description
Installs SSPL-LL

%prep

%post

# Copy config file and service startup to correct locations
cp /tmp/sspl-ll /etc/init.d
cp /tmp/sspl_ll.conf /etc

# Untar the service into /opt/seagate/sspl where it will execute from
mkdir -p /opt/seagate/sspl
tar xvzf /tmp/sspl-ll.tgz -C /opt/seagate/sspl

# Create the drivemanager directory
if [[ ! -d /tmp/dcs/drivemanager ]]; then 
   mkdir -p /tmp/dcs/drivemanager
fi

# Have the service startup at boot time
chkconfig sspl-ll on

# Start the service
systemctl start sspl-ll -l


%install
mkdir %{buildroot}/tmp
cp %_sourcedir/sspl-ll.tgz %{buildroot}/tmp
cp %_sourcedir/sspl-ll %{buildroot}/tmp
cp %_sourcedir/sspl_ll.conf %{buildroot}/tmp

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
/tmp/sspl-ll.tgz
/tmp/sspl-ll
/tmp/sspl_ll.conf

%changelog

