%define name libsspl_sec
%define version 0.0.1
%define release 1%{?dist}

Name:       %{name}
Version:    %{version}
Release:    %{release}
Summary:    Segate System Platform Library - Security
Group:      Libraries/System
License:    Seagate Proprietary
URL:        http://seagate.com
Source0:    %{name}-%{version}.tar.gz
Vendor:     Seagate Technology LLC
#BuildArch:  x86_64

BuildRequires: gcc doxygen python-lettuce python-pep8 pylint check-devel openssl-devel graphviz
#Requires:

%description
Segate System Platform Library - Security

A library used to sign and verify messages within SSPL.

%prep
%setup -q

%build
%configure
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
Requires:   %{name}=%{version}
%description method_none
This method doesn't actually do any signing.

%files method_none
/usr/lib64/libsspl_sec/sspl_none.so.0
/usr/lib64/libsspl_sec/sspl_none.so.0.0.0

%package devel
Summary:    Development files for %{name}
Requires:   %{name}=%{version} %{name}-method_none=%{version}
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
* Thu May 28 2015 Rich Gowman <rich.gowman@seagate.com> 0.0.1-1
- Initial RPM
