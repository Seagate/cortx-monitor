# build number
%define build_num  %( test -n "$build_number" && echo "$build_number" || echo 1 )

Name:       eos-sspl-test-lettuce-py2.7
Version:    %{version}
Release:    %{build_num}_git%{git_rev}%{?dist}
Summary:    Installs sspl-test scripts
BuildArch:  noarch
Group:      System Management
License:    Seagate Proprietary
URL:        http://gerrit.mero.colo.seagate.com:8080/#/admin/projects/sspl
Source0:    %{name}-%{version}.tgz
Requires:   sspl
BuildRoot:  %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)

%description
Installs SSPL sanity test scripts

%prep
%setup -n sspl/test

%clean
[ "${RPM_BUILD_ROOT}" != "/" ] && rm -rf ${RPM_BUILD_ROOT}

%install
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/eos/sspl/test
cp -rp . ${RPM_BUILD_ROOT}/opt/seagate/eos/sspl/test

%files
%defattr(-,sspl-ll,root,-)
/opt/seagate/eos/sspl/test

%changelog
* Fri Mar 22 2019 Madhura Mande <madhura.mande@seagate.com>
- SSPL sanity test spec file
