# build number
%define build_num  %( test -n "$build_number" && echo "$build_number" || echo 1 )

Name:       eos-libsspl_sec
Version:    %{version}
Release:    %{build_num}_git%{git_rev}%{?dist}
Summary:    Segate System Platform Library - Security
Group:      Libraries/System
License:    Seagate Proprietary
URL:        http://gerrit.mero.colo.seagate.com:8080/#/admin/projects/sspl
Source0:    eos-sspl-%{version}.tgz
Requires:   eos-sspl
BuildRoot:  %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
Vendor:     Seagate Technology LLC
#BuildArch:  x86_64

# For autogen step
BuildRequires: autoconf
BuildRequires: automake
BuildRequires: libtool
# For rest of build
BuildRequires: check-devel
BuildRequires: doxygen
BuildRequires: gcc
BuildRequires: graphviz
BuildRequires: make
BuildRequires: openssl-devel
BuildRequires: python-pep8
#Requires:

%description
Segate System Platform Library - Security

A library used to sign and verify messages within SSPL.

%prep
%setup -n sspl/libsspl_sec

%build
[ -f ./autogen.sh ] && bash ./autogen.sh
%configure --disable-tests PACKAGE_VERSION=%{version}
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

%package method_pki
Summary:    Uses PKI (RSA keys) for signature/verification for %{name}
Requires:   %{name} openssl-libs
%description method_pki
This method uses RSA keys to sign and verify messages.

%files method_pki
/usr/lib64/libsspl_sec/sspl_pki.so.0
/usr/lib64/libsspl_sec/sspl_pki.so.0.0.0

%package devel
Summary:    Development files for %{name}
Requires:   %{name} %{name}-method_none
%description devel
Includes headers for development against libsspl_sec.  Also includes .so files
for all method modules (ie sspl_none.so, sspl_pki.so).

%files devel
/usr/include/sspl_sec.h
/usr/lib64/libsspl_sec.a
/usr/lib64/libsspl_sec.la
/usr/lib64/libsspl_sec.so
/usr/lib64/libsspl_sec/sspl_none.a
/usr/lib64/libsspl_sec/sspl_none.la
/usr/lib64/libsspl_sec/sspl_none.so
/usr/lib64/libsspl_sec/sspl_pki.a
/usr/lib64/libsspl_sec/sspl_pki.la
/usr/lib64/libsspl_sec/sspl_pki.so
/usr/share/doc/libsspl_sec/html/*


%changelog
* Wed Jul 15 2015 Rich Gomwan <rich.gowman@seagate.com> 1.0.0-1
- Add sspl_pki method

* Mon Jun 01 2015 David Adair <dadair@seagate.com>
- Add jenkins-friendly template.  Convert to single tarball for all of sspl.

* Thu May 28 2015 Rich Gowman <rich.gowman@seagate.com> 0.0.1-1
- Initial RPM
