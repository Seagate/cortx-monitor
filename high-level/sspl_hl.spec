%define name sspl_hl
%define version 0.0.1
%define release 1%{?dist}
%define installpath %{buildroot}/opt/plex/apps

Name:       %{name}
Version:    %{version}
Release:    %{release}
Summary:    Seagate System Platform Library - High Level

Group:      Applications/System
License:    Seagate Proprietary
URL:        http://seagate.com
Source0:    %{name}-%{version}.tar.gz
Vendor:     Seagate Technology LLC
BuildArch:  noarch

BuildRequires: python >= 2.7.0
Requires:   PLEX

%description
Seagate System Platform Library - High Level

A cli (and library) that allow the user to control the cluster.


%prep
%setup -q


%build


%install
mkdir -p %{installpath}/sspl_hl/providers/service
install sspl_hl/main.py sspl_hl/__init__.py %{installpath}/sspl_hl/
install sspl_hl/providers/__init__.py %{installpath}/sspl_hl/providers/
install sspl_hl/providers/service/*.py %{installpath}/sspl_hl/providers/service/
mkdir -p %{buildroot}/usr/bin
install cli/cstor.py %{buildroot}/usr/bin/cstor


%files
%defattr(0755,root,root,-)
/usr/bin/cstor
%defattr(0644,plex,plex,-)
/opt/plex/apps/sspl_hl


%changelog
* Thu Apr 23 2015 Rich Gowman <rich.gowman@seagate.com> 0.0.1-1
- Initial RPM
