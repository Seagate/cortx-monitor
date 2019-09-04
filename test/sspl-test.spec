%define name sspl-test
%define url http://gerrit.mero.colo.seagate.com:8080/#/admin/projects/sspl

Name:       %{name}
Version:    %{version}
Release:    %{dist}
Summary:    Installs sspl-test scripts
BuildArch:  noarch
Group:      System Management
License:    Seagate Proprietary
URL:        %{url}
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
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/sspl/test
cp -rp . ${RPM_BUILD_ROOT}/opt/seagate/sspl/test

%files
%defattr(-,sspl-ll,root,-)
/opt/seagate/sspl/test

%changelog
* Fri Mar 22 2019 Madhura Mande <madhura.mande@seagate.com>
- SSPL sanity test spec file
