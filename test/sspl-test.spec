# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

# build number
%define build_num  %( test -n "$build_number" && echo "$build_number" || echo 1 )

Name:       cortx-sspl-test-lettuce-py2.7
Version:    %{version}
Release:    %{build_num}_git%{git_rev}%{?dist}
Summary:    Installs sspl-test scripts
BuildArch:  noarch
Group:      System Management
License:    Seagate
URL:        https://github.com/Seagate/cortx-sspl
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
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/cortx/sspl/test
cp -rp . ${RPM_BUILD_ROOT}/opt/seagate/cortx/sspl/test

%files
%defattr(-,sspl-ll,root,-)
/opt/seagate/cortx/sspl/test

%changelog
* Fri Mar 22 2019 Madhura Mande <madhura.mande@seagate.com>
- SSPL sanity test spec file
