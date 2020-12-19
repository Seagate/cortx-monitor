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

Name:       %{product_family}-sspl-test
Version:    %{version}
Release:    %{build_num}_git%{git_rev}%{?dist}
Summary:    Installs SSPL test for common test framework
BuildArch:  noarch
Group:      System Management
License:    Seagate
URL:        https://github.com/Seagate/cortx-sspl
Source0:    %{name}-%{version}.tgz
Requires:   %{product_family}-sspl = %{version}-%{release}
BuildRoot:  %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
Requires:  python36-psutil


%description
Installs SSPL sanity test ctf scripts

%prep
%setup -n %{parent_dir}/sspl_test

%build
%global __python %{__python3}

%clean
[ "${RPM_BUILD_ROOT}" != "/" ] && rm -rf ${RPM_BUILD_ROOT}

%install
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/%{product_family}/sspl/sspl_test
cp -rp . ${RPM_BUILD_ROOT}/opt/seagate/%{product_family}/sspl/sspl_test

%post
SSPL_DIR=/opt/seagate/%{product_family}/sspl

# Check and install required flask version
fl=`pip3.6 freeze | grep Flask`
if [[ -n $fl ]]; then
    ver=${fl##*=}
    if [[ "$ver" != "1.1.1" ]]; then
        # TODO: EOS-8145
        # Before uninstalling flask and its depedencies, add check if they are
        # installed already or version mismatch found during CORTX run time.
        # Jinja2 & MarkupSafe are already installed for salt configuration by provisioner.
        # Removing them would cause other resources to fail.
        pip3.6 uninstall -y flask
        pip3.6 install Flask==1.1.1
        #touch ${SSPL_DIR}/sspl_test/keep_flask
        #echo "$ver" > ${SSPL_DIR}/sspl_test/keep_flask
    else
        # Even correct Falsk version found, its depedencies (Jinja, MarkupSafe)
        # may not exist. Installing Falsk=1.1.1 again will get its depedencies.
        [ -z "$(pip3.6 freeze | grep Jinja2)" ] && pip3.6 install Flask==1.1.1
        [ -z "$(pip3.6 freeze | grep MarkupSafe)" ] && pip3.6 install Flask==1.1.1
    fi
else
    pip3.6 install Flask==1.1.1
    #touch ${SSPL_DIR}/sspl_test/keep_flask
fi

%preun
# Restore previous flask and its dependencies
# TODO: EOS-8145
#if [ -f /opt/seagate/%{product_family}/sspl/sspl_test/keep_flask ]; then
#    ver=`cat /opt/seagate/%{product_family}/sspl/sspl_test/keep_flask | sed 's/ *$//'`
#    rm -f /opt/seagate/%{product_family}/sspl/sspl_test/keep_flask
#    fl=`pip3.6 freeze | grep Flask`
#    if [[ -n $fl ]]; then
#        pip3.6 uninstall -y flask
#    fi
#    if [ "$ver" != "" ]; then
#        pip3.6 install Flask==$ver
#    fi
#fi

%files
%defattr(-,sspl-ll,root,-)
/opt/seagate/%{product_family}/sspl/sspl_test

%changelog
* Fri Dec 20 2019 Satish Darade <satish.darade@seagate.com>
- SSPL sanity test ctf spec file
