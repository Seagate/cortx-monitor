%define _unpackaged_files_terminate_build 0
%define _binaries_in_noarch_packages_terminate_build   0

# build number
%define build_num  %( test -n "$build_number" && echo "$build_number" || echo 1 )

Name:		%{product_family}-sspl-cli
Version:	%{version}
Release:	%{build_num}_git%{git_rev}%{?dist}
Summary:	Installs sspl_ll_cli
BuildArch:  noarch
Group:		System Management
License:	Seagate Proprietary
URL:		http://gerrit.mero.colo.seagate.com:8080/#/admin/projects/sspl
Source0:	%{name}-%{version}.tgz
Requires:   %{product_family}-sspl = %{version}-%{release}
BuildRoot:	%(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)

%description
Installs sspl_ll_cli

%prep
%setup -n cli

%clean
[ "${RPM_BUILD_ROOT}" != "/" ] && rm -rf ${RPM_BUILD_ROOT}

%install
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/%{product_family}/sspl/cli
cp -rp . ${RPM_BUILD_ROOT}/opt/seagate/%{product_family}/sspl/cli

%post
SSPL_DIR=/opt/seagate/%{product_family}/sspl
CFG_DIR=$SSPL_DIR/conf

[ -d "${SSPL_DIR}/cli/lib" ] && {
    ln -sf $SSPL_DIR/cli/lib/sspl_ll_cli /usr/bin/sspl_ll_cli
    ln -sf $SSPL_DIR/cli/lib/sspl_ll_cli $SSPL_DIR/cli/sspl_ll_cli
}

%files
%defattr(-,sspl-ll,root,-)
/opt/seagate/%{product_family}/sspl/cli

