#xyr build defines
# This section will be re-written by Jenkins build system.
%define _xyr_package_name     sspl-ll
%define _xyr_package_source   sspl-1.0.0.tgz
%define _xyr_package_version  1.0.0
%define _xyr_build_number     10.el7
%define _xyr_pkg_url          http://appdev-vm.xyus.xyratex.com:8080/view/OSAINT/job/OSAINT_sspl/
%define _xyr_svn_version      0
#xyr end defines

%define _unpackaged_files_terminate_build 0
%define _binaries_in_noarch_packages_terminate_build   0

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
Requires:   python-daemon python-zope-interface python-zope-event python-zope-component
Requires(pre): shadow-utils

%description
Installs SSPL-LL

%prep
%setup -n sspl/low-level

%build


%install
# Copy config file and service startup to correct locations

# CS-A identified by having a systemd directory for now
# TODO: Identify systems with facter facts
if [ -d "/etc/systemd" ]; then
    mkdir -p %{buildroot}/etc/systemd/system
    mkdir -p %{buildroot}/etc/dbus-1/system.d
    mkdir -p %{buildroot}/etc/polkit-1/rules.d
    mkdir -p %{buildroot}/etc/sspl-ll/templates/snmp
    cp files/sspl-ll.service %{buildroot}/etc/systemd/system
    cp files/sspl-ll_dbus_policy.conf %{buildroot}/etc/dbus-1/system.d
    cp files/sspl-ll_dbus_policy.rules %{buildroot}/etc/polkit-1/rules.d
    cp files/sspl_ll.conf %{buildroot}/etc
else
    # CS-LG are non-systemd
    mkdir -p %{buildroot}/etc
    cp files/sspl_ll_cs.conf %{buildroot}/etc/sspl_ll.conf
    cp files/sspl-ll %{buildroot}/etc/init.d
fi

# Copy the service into /opt/seagate/sspl where it will execute from
mkdir -p %{buildroot}/opt/seagate/sspl/low-level
cp -rp . %{buildroot}/opt/seagate/sspl/low-level


%post

# Config for CS-A identified by having systemd available
if [ -d "/etc/systemd" ]; then
    # Add the sspl-ll user if it doesn't exist
    echo "SSPL-LL: creating sspl-ll user"
        id -u sspl-ll &>/dev/null || /usr/sbin/useradd -r -g zabbix \
	    -s /sbin/nologin  \
	    -c "User account to run the sspl-ll service" sspl-ll

    cp -f /opt/seagate/sspl/low-level/files/sspl_ll.conf /etc
    cp -f /opt/seagate/sspl/low-level/files/sspl-ll.service /etc/systemd/system

    mkdir -p /var/log/journal
    systemctl restart systemd-journald

    # Have systemd reload
    systemctl daemon-reload

    # Enable services to start at boot
    systemctl enable sspl-ll
    systemctl enable rabbitmq-server

    # Restart dbus with new policy files
    systemctl restart dbus
else
    # CS-LG are non-systemd

    # Add the sspl-ll user
	id -u sspl-ll &>/dev/null || /usr/sbin/useradd \
		-s /sbin/nologin  \
		-c "User account to run the sspl-ll service" sspl-ll

    # Change ownership to sspl-ll user
	chown -R sspl-ll:root /opt/seagate/sspl/low-level
	
    cp -f /opt/seagate/sspl/low-level/files/sspl_ll_cs.conf /etc/sspl_ll.conf
    cp -f /opt/seagate/sspl/low-level/files/sspl-ll /etc/init.d

    # Create a link to low-level cli for easy global access
    ln -sf /opt/seagate/sspl/low-level/cli/sspl-ll-cli /usr/bin

    # Enable services to start at boot
    chkconfig rabbitmq-server on
    chkconfig sspl-ll on
fi


%clean
rm -rf %{buildroot}


%files
%defattr(-,sspl-ll,root,-)
/opt/seagate/sspl/*


%changelog
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
