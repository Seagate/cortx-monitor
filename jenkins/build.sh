#!/bin/bash

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

set -e

BUILD_START_TIME=$(date +%s)
BASE_DIR=$(realpath $(dirname $0)/..)

PROG_NAME=$(basename $0)
source "$BASE_DIR/low-level/files/opt/seagate/sspl/bin/constants.sh"

RPM_BUILD_PATH=${DIST:-$HOME/rpmbuild}

usage() {
    echo "usage: $PROG_NAME [-g <git version>] [-v <sspl version>]
                            [-p <product_name>] [-t <true|false>]
                            [-l <DEBUG|INFO|WARNING|ERROR|CRITICAL>]" 1>&2;
    exit 1;
}

while getopts ":g:v:p:t:l:" o; do
    case "${o}" in
        g)
            GIT_VER=${OPTARG}
            ;;
        v)
            VERSION=${OPTARG}
            ;;
        p)
            PRODUCT=${OPTARG}
            ;;
        t)
            TEST=true
            ;;
        l)
            LOG_LEVEL=${OPTARG}
            ;;
        *)
            usage
            ;;
    esac
done

cd $BASE_DIR
[ -z "$GIT_VER" ] && GIT_VER=$(git rev-parse --short HEAD)
[ -z "$VERSION" ] && VERSION=$(cat $BASE_DIR/VERSION)
[ -z "$PRODUCT" ] && PRODUCT="cortx"
[ -z "$TEST" ] && TEST=true
[ -z "$CLI" ] && CLI=true

# validate build requested log level
case $LOG_LEVEL in
    "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")
        echo "${LOG_LEVEL}" > $BASE_DIR/low-level/files/opt/seagate/sspl/conf/build-requested-loglevel;;
    "");;
    *)
        echo "Invalid log level '$LOG_LEVEL' requested. Please use either of DEBUG, INFO, WARNING, ERROR, CRITICAL"
        usage
esac
echo "Using VERSION=${VERSION} GIT_VER=${GIT_VER} PRODUCT=${PRODUCT} TEST=${TEST} LOG_LEVEL=${LOG_LEVEL} "

################### INSTALL REQUIRED RPM PACKAGES ##############################

# Check python package
req_file=$BASE_DIR/low-level/requirements.txt
echo "Installing python packages..."
python3 -m pip install -r "$req_file"  > /dev/null || {
    echo "Unable to install package from $req_file"; exit 1;
};

#Check & install required RPM packages
echo "Installing build required RPM packages..."
yum install -y python36-dbus python36-paramiko \
    python36-psutil python36-gobject cortx-py-utils

echo "Generating tar & RPM's for pre requisite packages systemd_python."
yum erase -y systemd-python36-*

echo 'Installing systemd-python36*...'
yum install -y systemd-python36-*

################### TAR & RPM BUILD ##############################

# Remove existing directory tree and create fresh one.
TAR_START_TIME=$(date +%s)
cd $BASE_DIR
rm -rf ${RPM_BUILD_PATH}
mkdir -p ${RPM_BUILD_PATH}/SOURCES
TOPDIR=$(realpath $RPM_BUILD_PATH)
echo $TOPDIR

# Create tar for sspl
echo "Creating tar for sspl build"
if [ "$TEST" == true ]
then
    tar -czvf "${RPM_BUILD_PATH}"/SOURCES/"$PRODUCT_FAMILY"-sspl-test-"${VERSION}".tgz -C "${BASE_DIR}"/.. "${PRODUCT_FAMILY}"-sspl/sspl_test
fi

if [ "$CLI" == true ]
then
    tar -czvf "${RPM_BUILD_PATH}"/SOURCES/"$PRODUCT_FAMILY"-sspl-cli-"${VERSION}".tgz -C "${BASE_DIR}"/.. "${PRODUCT_FAMILY}"-sspl/low-level/cli
fi

tar -czvf "${RPM_BUILD_PATH}"/SOURCES/"$PRODUCT_FAMILY"-sspl-"${VERSION}".tgz -C "${BASE_DIR}"/.. "${PRODUCT_FAMILY}"-sspl/low-level "${PRODUCT_FAMILY}"-sspl/libsspl_sec

TAR_END_TIME=$(date +%s)
echo "Generated tar for sspl build"

################### RPM builds for SSPL ##############################
echo "Generating rpm's for sspl build"
RPM_BUILD_START_TIME=$(date +%s)

rpmbuild --define "version $VERSION" --define "git_rev $GIT_VER" \
    --define "_topdir $TOPDIR" --define "product_family $PRODUCT_FAMILY" -bb "$BASE_DIR"/low-level/sspl-ll.spec
rpmbuild --define "version $VERSION" --define "git_rev $GIT_VER" \
    --define "_topdir $TOPDIR" --define "product_family $PRODUCT_FAMILY" -bb "$BASE_DIR"/libsspl_sec/libsspl_sec.spec

if [ "$CLI" == true ]
then
    rpmbuild --define "version $VERSION" --define "git_rev $GIT_VER" \
        --define "_topdir $TOPDIR" --define "product_family $PRODUCT_FAMILY" -bb "$BASE_DIR"/low-level/cli/sspl_cli.spec
fi

if [ "$TEST" == true ]
then
    rpmbuild --define "version $VERSION" --define "git_rev $GIT_VER" \
        --define "_topdir $TOPDIR" --define "product_family $PRODUCT_FAMILY" -bb "$BASE_DIR"/sspl_test/sspl-test.spec
fi

RPM_BUILD_END_TIME=$(date +%s)
echo "Generated rpm's for sspl build"

# remove systemd-python36
yum erase -y systemd-python36-*

BUILD_END_TIME=$(date +%s)

TAR_DIFF=$(( "$TAR_END_TIME" - "$TAR_START_TIME" ))
printf "TAR CREATION TIME ==========> "
printf "%02d:%02d:%02d\n" $(( TAR_DIFF / 3600 )) $(( ( TAR_DIFF / 60 ) % 60 )) $(( TAR_DIFF % 60 ))

RPM_BUILD_DIFF=$(( "$RPM_BUILD_END_TIME" - "$RPM_BUILD_START_TIME" ))
printf "RPM BUILD TIME ==========> "
printf "%02d:%02d:%02d\n" $(( RPM_BUILD_DIFF / 3600 )) $(( ( RPM_BUILD_DIFF / 60 ) % 60 )) $(( RPM_BUILD_DIFF % 60 ))

BUILD_DIFF=$(( "$BUILD_END_TIME" - "$BUILD_START_TIME" ))
printf "COMPLETE BUILD TIME ==========> "
printf "%02d:%02d:%02d\n" $(( BUILD_DIFF / 3600 )) $(( ( BUILD_DIFF / 60 ) % 60 )) $(( BUILD_DIFF % 60 ))

echo -e "\nGenerated RPMs..."
find $RPM_BUILD_PATH -name "*.rpm"
