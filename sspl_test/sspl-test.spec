%define _unpackaged_files_terminate_build 0
%define _binaries_in_noarch_packages_terminate_build   0

# build number
%define build_num  %( test -n "$build_number" && echo "$build_number" || echo 1 )

Name:       sspl-test
Version:    %{version}
Release:    %{build_num}_git%{git_rev}%{?dist}
Summary:    Installs SSPL test for common test framework
BuildArch:  noarch
Group:      System Management
License:    Seagate Proprietary
URL:        http://gerrit.mero.colo.seagate.com:8080/#/admin/projects/sspl
Source0:    %{name}-%{version}.tgz
Requires:   sspl
BuildRoot:  %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)


%description
Installs SSPL sanity test ctf scripts

%prep
%setup -n sspl_test

%clean
[ "${RPM_BUILD_ROOT}" != "/" ] && rm -rf ${RPM_BUILD_ROOT}

%install
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/sspl/sspl_test
cp -rp . ${RPM_BUILD_ROOT}/opt/seagate/sspl/sspl_test

%post
SSPL_DIR=/opt/seagate/sspl
CFG_DIR=$SSPL_DIR/conf

[ -d "${SSPL_DIR}/sspl_test/lib" ] && {
    ln -sf $SSPL_DIR/sspl_test/lib/sspl_tests /usr/bin/sspl_tests
}

%files
%defattr(-,sspl-ll,root,-)
/opt/seagate/sspl/sspl_test

%changelog
* Fri Dec 20 2019 Satish Darade <satish.darade@seagate.com>
- SSPL sanity test ctf spec file
