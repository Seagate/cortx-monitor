##############################################################################
# - Why systemd-python36 is packaged separately ?
#   The current package available in CentOS 7.7 YUM repository supports Python
#   2.7. When SSPL runs using Python 3.6 it requires same package but with
#   Python 3.6 support which is not available in CentOS 7.7 repository.
#   It is available in PyPI repository but that requires compiling some part
#   developed using C. This compilation requires gcc, systemd-deve and Python36
#   -devel package. Production system may not have these packages and so We
#   need to pre-compile this package and supply with SSPL.
#   This package can be removed when systemd-python package for Python 3.6 is
#   available in YUM repository.
##############################################################################

# build number
%define build_num  %( test -n "$build_number" && echo "$build_number" || echo 1 )

Name: systemd-python36
Version: %{version}
Release: %{build_num}_git%{git_rev}%{?dist}
Summary: Installs Python wrappers for Systemd functionality
Group: System Management
License: Seagate Proprietary
URL: https://github.com/systemd/python-systemd
Source0: %{name}-%{version}.tgz
BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
Requires: python36
BuildRequires: python36

%description
Python wrapper for Systemd functionality

%prep
%setup -n sspl/systemd-python36

%clean
[ "${RPM_BUILD_ROOT}" != "/" ] && rm -rf ${RPM_BUILD_ROOT}

%install
mkdir -p ${RPM_BUILD_ROOT}/usr/lib64/python3.6/site-packages/systemd
cp -rp . ${RPM_BUILD_ROOT}/usr/lib64/python3.6/site-packages/systemd

%files
/usr/lib64/python3.6/site-packages/systemd



%changelog
* Tue Jan 14 2020 Malhar Vora <malhar.vora@seagate.com>
- SPEC file for systemd-python36 package
