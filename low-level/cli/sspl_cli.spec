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

Name:		%{product_family}-sspl-cli
Version:	%{version}
Release:	%{build_num}_git%{git_rev}%{?dist}
Summary:	Installs sspl_ll_cli
BuildArch:  noarch
Group:		System Management
License:	Seagate
URL:		https://github.com/Seagate/cortx-sspl
Source0:	%{name}-%{version}.tgz
Requires:   %{product_family}-sspl = %{version}-%{release}
BuildRoot:	%(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)

%description
Installs sspl_ll_cli

%prep
%setup -n %{parent_dir}/low-level/cli

%clean
[ "${RPM_BUILD_ROOT}" != "/" ] && rm -rf ${RPM_BUILD_ROOT}

%install
SSPL_BASE=${RPM_BUILD_ROOT}/opt/seagate/%{product_family}/sspl
mkdir -p $SSPL_BASE/low-level/cli
cp -rp . $SSPL_BASE/low-level/cli

%post
SSPL_DIR=/opt/seagate/%{product_family}/sspl
# Coping independent executable script inside sspl/low-level to easier access core code access.
cp -p $SSPL_DIR/low-level/cli/sspl-ll-cli $SSPL_DIR/low-level/

[ -d "${SSPL_DIR}/low-level/cli" ] && {
    ln -sf $SSPL_DIR/low-level/sspl-ll-cli /usr/bin/sspl-ll-cli
}

%postun
rm -f $SSPL_DIR/low-level/sspl-ll-cli
rm -f /usr/bin/sspl-ll-cli

%files
%defattr(-,root,root,-)
/opt/seagate/%{product_family}/sspl/low-level/cli
