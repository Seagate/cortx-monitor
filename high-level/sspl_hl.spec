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

#xyr build defines
# This section will be re-written by Jenkins build system.
%if 0%{?rhel} == 7
    %define dist .el7
%endif
%define _xyr_package_name     sspl_hl
%define _xyr_package_source   sspl-1.0.0.tgz
%define _xyr_package_version  1.0.0
%define _xyr_build_number     1%{dist}
%define _xyr_pkg_url          http://es-gerrit:8080/sspl
%define _xyr_svn_version      0
#xyr end defines

%define installpath %{buildroot}/opt/plex/apps

Name:       %{_xyr_package_name}
Version:    %{_xyr_package_version}
Release:    %{_xyr_build_number}
Summary:    Seagate System Platform Library - High Level

Group:      Applications/System
License:    Seagate
URL:        %{_xyr_pkg_url}
Source0:    %{_xyr_package_source}
Vendor:     Seagate Technology LLC
BuildArch:  noarch

BuildRequires: python
Requires:   PLEX, python-paramiko, python-dateutil, botocore, boto3, jmespath, xmltodict, PyYAML

%description
Seagate System Platform Library - High Level

A cli (and library) that allow the user to control the cluster.


%prep

%setup -q -n sspl/high-level


%build


%install
mkdir -p %{installpath}/
cp -afv sspl_hl %{installpath}/


mkdir -p %{buildroot}/%{python_sitelib}
cp -afv cstor %{buildroot}/%{python_sitelib}/

mkdir -p %{buildroot}/usr/bin
ln -s %{python_sitelib}/cstor/cli/main.py %{buildroot}/usr/bin/cstor

mkdir -p %{buildroot}/var/lib/support_bundles

%files
%defattr(0644,plex,plex,-)
%{python_sitelib}/cstor
/opt/plex/apps/sspl_hl
%defattr(0755,root,root,-)
/usr/bin/cstor
%{python_sitelib}/cstor/cli/main.py
%defattr(0777,plex,plex,-)
/var/lib/support_bundles



%changelog
* Thu Oct 19 2017 Oleg Gut <oleg.gut@seagate.com>
- replaced hardcodes with macroses in spec, removed redundant code

* Mon Mar 28 2016 Bhupesh Pant <Bhupesh.Pant@seagate.com>
- Added support_bundle and cluster_node_manager modules in utils .

* Tue Mar 22 2016 Harshada Tupe <harshada.tupe@seagate.com>
- Changed support_bundles directory permissions.

* Thu Feb 18 2016 Bhupesh Pant <bhupesh.pant@seagate.com>
- Changed support_bundle to bundle

* Wed Jan 06 2016 Bhupesh Pant <bhupesh.pant@seagate.com>
- Removed auth.propeties files

* Mon Dec 28 2015 Bhupesh Pant <bhupesh.pant@seagate.com>
- Removed all the unnecessary providers

* Sat Nov 14 2015 Bhupesh Pant <bhupesh.pant@seagate.com>
- Add status provider

* Fri Sep 11 2015 Madhur Nawandar <madhur.nawandar@seagate.com>
- Add support_bundle provider
- Created directory to store support bundles

* Mon Aug 31 2015 Malhar Vora <malhar.vora@seagate.com>
- Add power and fru providers

* Tue Aug 04 2015 Rich Gowman <rich.gowman@seagate.com>
- Add service and node providers
- Add common utils package (used by various providers)

* Thu Jul 23 2015 Rich Gowman <rich.gowman@seagate.com>
- Migrate cstor cli from single script to python module

* Mon Jun 01 2015 David Adair <dadair@seagate.com>
- Add jenkins-friendly template.  Convert to single tarball for all of sspl.

* Thu Apr 23 2015 Rich Gowman <rich.gowman@seagate.com> 0.0.1-1
- Initial RPM
