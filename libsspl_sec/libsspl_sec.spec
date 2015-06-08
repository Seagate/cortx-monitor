#xyr build defines
# This section will be re-written by Jenkins build system.
%define _xyr_package_name     libsspl_sec
%define _xyr_package_source   sspl-1.0.0.tgz
%define _xyr_package_version  1.0.0
%define _xyr_build_number     1.el7
%define _xyr_pkg_url          http://es-gerrit:8080/sspl
%define _xyr_svn_version      0
#xyr end defines

Name:       %{_xyr_package_name}
Version:    %{_xyr_package_version}
Release:    %{_xyr_build_number}
Summary:    Segate System Platform Library - Security
Group:      Libraries/System
License:    Seagate Proprietary
URL:        %{_xyr_pkg_url}
Source0:    %{_xyr_package_source}
Vendor:     Seagate Technology LLC
#BuildArch:  x86_64

# For autogen step
BuildRequires: libtool autoconf automake
# For rest of build
BuildRequires: gcc doxygen python-lettuce python-pep8 pylint check-devel openssl-devel graphviz
#Requires:

# Temporary requirement on method_none.  This should eventually change to
# ensure one method is installed (though doesn't matter which.)  Use rpm
# provides mechanism.
Requires: libsspl_sec-method_none

%description
Segate System Platform Library - Security

A library used to sign and verify messages within SSPL.

%prep
%setup -n sspl/libsspl_sec

%build
[ -f ./autogen.sh ] && bash ./autogen.sh
%configure PACKAGE_VERSION=%{version}
make

%install
%makeinstall

%files
/usr/lib64/libsspl_sec.so.0
/usr/lib64/libsspl_sec.so.0.0.0

%post -p /sbin/ldconfig
%postun -p /sbin/ldconfig


%package method_none
Summary:    The 'null' signature method for %{name}
Requires:   %{name}
%description method_none
This method does not actually do any signing.

%files method_none
/usr/lib64/libsspl_sec/sspl_none.so.0
/usr/lib64/libsspl_sec/sspl_none.so.0.0.0

%package devel
Summary:    Development files for %{name}
Requires:   %{name} %{name}-method_none
%description devel
Includes headers for development against libsspl_sec.  Also includes .so files
for all method modules (ie sspl_none.so).

%files devel
/usr/include/sspl_sec.h
/usr/lib64/libsspl_sec.a
/usr/lib64/libsspl_sec.la
/usr/lib64/libsspl_sec.so
/usr/lib64/libsspl_sec/sspl_none.a
/usr/lib64/libsspl_sec/sspl_none.la
/usr/lib64/libsspl_sec/sspl_none.so
/usr/share/doc/libsspl_sec/html/*


%changelog
* Mon Jun 01 2015 David Adair <dadair@seagate.com>
- Add jenkins-friendly template.  Convert to single tarball for all of sspl.

* Thu May 28 2015 Rich Gowman <rich.gowman@seagate.com> 0.0.1-1
- Initial RPM
