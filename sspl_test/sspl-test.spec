%define _unpackaged_files_terminate_build 0
%define _binaries_in_noarch_packages_terminate_build   0

# build number
%define build_num  %( test -n "$build_number" && echo "$build_number" || echo 1 )

Name:       %{product_family}-sspl-test
Version:    %{version}
Release:    %{build_num}_git%{git_rev}%{?dist}
Summary:    Installs SSPL test for common test framework
BuildArch:  noarch
Group:      System Management
License:    Seagate Proprietary
URL:        http://gerrit.mero.colo.seagate.com:8080/#/admin/projects/sspl
Source0:    %{name}-%{version}.tgz
Requires:   %{product_family}-sspl
BuildRoot:  %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)
Requires:  python36-psutil


%description
Installs SSPL sanity test ctf scripts

%prep
%setup -n sspl_test

%clean
[ "${RPM_BUILD_ROOT}" != "/" ] && rm -rf ${RPM_BUILD_ROOT}

%install
mkdir -p ${RPM_BUILD_ROOT}/opt/seagate/%{product_family}/sspl/sspl_test
cp -rp . ${RPM_BUILD_ROOT}/opt/seagate/%{product_family}/sspl/sspl_test

%post
SSPL_DIR=/opt/seagate/%{product_family}/sspl
CFG_DIR=$SSPL_DIR/conf

# Check and install required flask version
fl=`pip3.6 freeze | grep Flask`
if [[ -n $fl ]]; then
    ver=${fl##*=}
    if [[ "$ver" != "1.1.1" ]]; then
        # TODO: EOS-8145
        # Before uninstalling flask and its depedencies, add check if they are
        # installed already or version mismatch found during EOS run time.
        # Jinja2 & MarkupSafe are already installed for salt configuration by provisioner.
        # Removing them would cause other resources to fail.
        pip3.6 uninstall -y flask
        pip3.6 install Flask==1.1.1
        #touch ${SSPL_DIR}/sspl_test/keep_flask
        #echo "$ver" > ${SSPL_DIR}/sspl_test/keep_flask
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
