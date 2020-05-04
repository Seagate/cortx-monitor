%define _unpackaged_files_terminate_build 0
%define _binaries_in_noarch_packages_terminate_build   0

# build number
%define build_num  %( test -n "$build_number" && echo "$build_number" || echo 1 )

Name:       %{product}-sspl-test
Version:    %{version}
Release:    %{build_num}_git%{git_rev}%{?dist}
Summary:    Installs SSPL test for common test framework
BuildArch:  noarch
Group:      System Management
License:    Seagate Proprietary
URL:        http://gerrit.mero.colo.seagate.com:8080/#/admin/projects/sspl
Source0:    %{name}-%{version}.tgz
Requires:   %{product}-sspl
BuildRoot:  %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
Requires:  python36-psutil


%description
Installs SSPL sanity test ctf scripts

%prep
%setup -n sspl_test

%clean
[ "${RPM_BUILD_ROOT}" != "/" ] && rm -rf ${RPM_BUILD_ROOT}

%install
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/%{product}/sspl/sspl_test
cp -rp . ${RPM_BUILD_ROOT}/opt/seagate/%{product}/sspl/sspl_test

%post
SSPL_DIR=/opt/seagate/%{product}/sspl
CFG_DIR=$SSPL_DIR/conf

# Check and install required flask version
flask_installed=$(python3.6 -c 'import pkgutil; print(1 if pkgutil.find_loader("flask") else 0)')
[ $flask_installed == "1" ] && touch ${SSPL_DIR}/sspl_test/keep_flask &&
[ $(python3.6 -c 'import flask; print(flask.__version__)') = "1.1.1" ] || {
    if [ $flask_installed == "1" ]; then
        $sudo pip3.6 uninstall -y flask
    fi
    $sudo pip3.6 install flask==1.1.1
}

%preun
# Uninstall flask and all its dependencies if it was not already installed
[ -f /opt/seagate/%{product}/sspl/sspl_test/keep_flask ] && rm -f /opt/seagate/%{product}/sspl/sspl_test/keep_flask || {
    $sudo pip3.6 uninstall -y flask Werkzeug itsdangerous Jinja2 click MarkupSafe
}

%files
%defattr(-,sspl-ll,root,-)
/opt/seagate/%{product}/sspl/sspl_test

%changelog
* Fri Dec 20 2019 Satish Darade <satish.darade@seagate.com>
- SSPL sanity test ctf spec file
