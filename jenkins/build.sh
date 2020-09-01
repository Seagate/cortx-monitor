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
. "$BASE_DIR/low-level/files/opt/seagate/sspl/bin/constants.sh"
# keeping the rpmbuild path as it is to make the build green.
RPM_BUILD_PATH=${DIST:-$HOME/rpmbuild}
DIST=$(realpath $BASE_DIR/dist)

usage() {
    echo "usage: $PROG_NAME [-g <git version>] [-v <sspl version>] [-k <key>]
                            [-p <product_name>] [-t <true|false>]
                            [-l <DEBUG|INFO|WARNING|ERROR|CRITICAL>]" 1>&2;
    exit 1;
}

while getopts ":g:v:p:k:t:l:" o; do
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
        k)
            KEY=${OPTARG}
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

#product and key for sspl pyinstaller
[ -z "$PRODUCT" ] && PRODUCT="cortx"
[ -z "$KEY" ] && KEY="cortx@ldr_r1@sspl@pr0duct"
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

################### COPY FRESH DIR ##############################
COPY_START_TIME=$(date +%s)
DIST="$BASE_DIR/dist"
TMPDIR="$DIST/tmp"

[ -d "$TMPDIR" ] && {
    rm -rf ${TMPDIR}
}
mkdir -p $DIST/sspl/bin $DIST/sspl/conf $DIST/sspl/resources/actuators $DIST/sspl/resources/sensors $DIST/sspl/resources/iem/iec_mapping $TMPDIR

cp -R $BASE_DIR/low-level/snmp $DIST/sspl/conf
cp -R $BASE_DIR/low-level/files/opt/seagate/sspl/bin/* $DIST/sspl/bin
cp -R $BASE_DIR/low-level/requirements.txt $DIST/sspl/conf/requirements.txt
cp -R $BASE_DIR/low-level/framework/utils/service_logging.py $DIST/sspl/bin/service_logging.py
cp -R $BASE_DIR/low-level/framework/utils/utility.py $DIST/sspl/bin/utility.py
cp -R $BASE_DIR/low-level/framework/utils/salt_util.py $DIST/sspl/bin/salt_util.py
cp -R $BASE_DIR/low-level/framework/base/sspl_constants.py $DIST/sspl/bin/sspl_constants.py
cp -R $BASE_DIR/low-level/framework/base/sspl_conf_adopt.py $DIST/sspl/bin/sspl_conf_adopt.py
cp -R $BASE_DIR/low-level/framework/utils/config_reader.py $DIST/sspl/bin/config_reader.py
cp -R $BASE_DIR/low-level/framework/sspl_init $DIST/sspl/bin
cp -R $BASE_DIR/low-level/framework/sspl_reinit $DIST/sspl/bin
cp -R $BASE_DIR/low-level/framework/sspl_rabbitmq_reinit $DIST/sspl/bin
cp -R $BASE_DIR/low-level/json_msgs/schemas/actuators/*.json $DIST/sspl/resources/actuators
cp -R $BASE_DIR/low-level/json_msgs/schemas/sensors/*.json $DIST/sspl/resources/sensors

cp -R $BASE_DIR/low-level/files/iec_mapping/* $DIST/sspl/resources/iem/iec_mapping

cp -R $BASE_DIR/libsspl_sec/ $DIST/sspl
cp -R $BASE_DIR/systemd-python36/ $DIST/sspl

CONF=$BASE_DIR/low-level/files
cp -R $CONF/opt/seagate/sspl/conf/* $CONF/etc $DIST/sspl/conf
cp $BASE_DIR/low-level/sspl-ll.spec $TMPDIR
cp $BASE_DIR/low-level/cli/sspl_cli.spec $TMPDIR
cp $BASE_DIR/libsspl_sec/libsspl_sec.spec $TMPDIR
cp $BASE_DIR/sspl_test/sspl-test.spec $TMPDIR
cp $BASE_DIR/systemd-python36/systemd-python36.spec $TMPDIR
COPY_END_TIME=$(date +%s)

################### PYINSTALLER for SSPL ##############################
# Copy source and test files, create dir structure
CORE_BUILD_START_TIME=$(date +%s)
cd $TMPDIR
mkdir -p $DIST/sspl/lib $DIST/sspl/bin $DIST/sspl/conf $TMPDIR $TMPDIR/sspl
cp -rs $BASE_DIR/low-level/ $TMPDIR/sspl
cp -rs $BASE_DIR/libsspl_sec/ $TMPDIR/sspl

# Enable SSPL package for python imports
export PYTHONPATH=$TMPDIR/sspl/:$TMPDIR/sspl_test:$PYTHONPATH

# Check python package
req_file=$BASE_DIR/low-level/requirements.txt
echo "Installing python packages..."
python3 -m pip install --user -r $req_file  > /dev/null || {
    echo "Unable to install package from $req_file"; exit 1;
};

#Check & install required RPM packages
echo "Installing build required RPM packages..."
yum install -y python36-dbus python36-paramiko \
    python36-psutil python36-gobject eos-py-utils

echo "Generating tar & RPM's for pre requisite packages systemd_python."
yum erase -y systemd-python36-*
cd $BASE_DIR
rm -rf ${RPM_BUILD_PATH}
mkdir -p ${RPM_BUILD_PATH}/SOURCES
TOPDIR=$(realpath $RPM_BUILD_PATH)
echo $TOPDIR

tar -czvf ${RPM_BUILD_PATH}/SOURCES/systemd-python36-${VERSION}.tgz -C ${BASE_DIR}/.. cortx-sspl/systemd-python36
rpmbuild --define "version $VERSION" --define "git_rev $GIT_VER" --define "_topdir $TOPDIR" -bb $BASE_DIR/systemd-python36/systemd-python36.spec

echo 'Installing systemd-python36*...'
yum install -y ${RPM_BUILD_PATH}/RPMS/x86_64/systemd-python36-*

if [ "$TEST" == true ]
then
    mkdir -p $TMPDIR/sspl_test $DIST/sspl_test $DIST/sspl_test/conf
    cp -R $BASE_DIR/sspl_test/* $TMPDIR/sspl_test
    PYINSTALLER_FILE=$TMPDIR/${PRODUCT}_sspl_test.spec
    cp $BASE_DIR/jenkins/pyinstaller/run_test.spec ${PYINSTALLER_FILE}
    cp -R $BASE_DIR/sspl_test/constants.sh $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/mock_data $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/plans $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/run_tests.sh $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/run_qa_test.sh $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/run_sspl-ll_tests.sh $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/set_threshold.sh $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/mock_server $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/rabbitmq_start_checker $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/sspl_tests.conf $DIST/sspl_test/conf
    cp -R $BASE_DIR/sspl_test/ipmi_simulator $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/put_config_to_consul.py $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/generate_test_report.py $DIST/sspl_test

    echo "Executing pyinstaller..."
    sed -i -e "s|<PRODUCT>|${PRODUCT}|g" \
            -e "s|<SSPL_TEST_PATH>|${TMPDIR}/sspl_test|g" \
            -e "s|<SSPL_PATH>|${TMPDIR}/sspl|g" ${PYINSTALLER_FILE}
    python3 -m PyInstaller --clean -y --distpath ${DIST}/sspl_test --key ${KEY} ${PYINSTALLER_FILE}
fi

if [ "$CLI" == true ]
then
    mkdir -p $TMPDIR/cli $DIST/cli $DIST/cli/actuator_msgs
    cp -R $BASE_DIR/low-level/cli/* $TMPDIR/cli
    cp -R $BASE_DIR/low-level/tests/manual/actuator_msgs/*.json $DIST/cli/actuator_msgs
    cp -R $BASE_DIR/low-level/tests/manual/actuator_msgs/*.conf $DIST/cli/actuator_msgs

    PYINSTALLER_FILE=$TMPDIR/${PRODUCT}_sspl.spec
    cp $BASE_DIR/jenkins/pyinstaller/sspl_ll_cli.spec ${PYINSTALLER_FILE}
    echo "Executing pyinstaller..."
    sed -i -e "s|<PRODUCT>|${PRODUCT}|g" \
        -e "s|<SSPL_CLI_PATH>|${TMPDIR}/cli|g" \
        -e "s|<SSPL_PATH>|${TMPDIR}/sspl|g" ${PYINSTALLER_FILE}
    python3 -m PyInstaller --clean -y --distpath ${DIST}/cli --key ${KEY} ${PYINSTALLER_FILE}
fi

# Create spec for pyinstaller
PYINSTALLER_FILE=$TMPDIR/${PRODUCT}_sspl.spec
cp $BASE_DIR/jenkins/pyinstaller/sspl.spec ${PYINSTALLER_FILE}
echo "Executing pyinstaller..."
sed -i -e "s|<PRODUCT>|${PRODUCT}|g" \
        -e "s|<SSPL_PATH>|${TMPDIR}/sspl|g" ${PYINSTALLER_FILE}
python3 -m PyInstaller --clean -y --distpath ${DIST}/sspl --key ${KEY} ${PYINSTALLER_FILE}

CORE_BUILD_END_TIME=$(date +%s)

COPY_DIFF=$(( $COPY_END_TIME - $COPY_START_TIME ))
printf "COPY TIME!!!!!!!!!!!!"
printf "%02d:%02d:%02d\n" $(( COPY_DIFF / 3600 )) $(( ( COPY_DIFF / 60 ) % 60 )) $(( COPY_DIFF % 60 ))

CORE_DIFF=$(( $CORE_BUILD_END_TIME - $CORE_BUILD_START_TIME ))
printf "CORE BUILD TIME!!!!!!!!!!!!"
printf "%02d:%02d:%02d\n" $(( CORE_DIFF / 3600 )) $(( ( CORE_DIFF / 60 ) % 60 )) $(( CORE_DIFF % 60 ))

################### TAR & RPM BUILD ##############################

# Remove existing directory tree and create fresh one.
TAR_START_TIME=$(date +%s)

# Create tar for sspl
echo "Creating tar for sspl build"
if [ "$TEST" == true ]
then
    tar -czvf ${RPM_BUILD_PATH}/SOURCES/$PRODUCT_FAMILY-sspl-test-${VERSION}.tgz -C ${DIST} sspl_test
fi

if [ "$CLI" == true ]
then
tar -czvf ${RPM_BUILD_PATH}/SOURCES/$PRODUCT_FAMILY-sspl-cli-${VERSION}.tgz -C ${DIST} cli
fi

tar -czvf ${RPM_BUILD_PATH}/SOURCES/$PRODUCT_FAMILY-sspl-${VERSION}.tgz -C ${DIST} sspl

TAR_END_TIME=$(date +%s)
echo "Generated tar for sspl build"

################### RPM builds for SSPL ##############################
echo "Generating rpm's for sspl build"
RPM_BUILD_START_TIME=$(date +%s)

rpmbuild --define "version $VERSION" --define "git_rev $GIT_VER" \
    --define "_topdir $TOPDIR" --define "product_family $PRODUCT_FAMILY" -bb $TMPDIR/sspl-ll.spec
rpmbuild --define "version $VERSION" --define "git_rev $GIT_VER" \
    --define "_topdir $TOPDIR" --define "product_family $PRODUCT_FAMILY" -bb $TMPDIR/libsspl_sec.spec

if [ "$CLI" == true ]
then
rpmbuild --define "version $VERSION" --define "git_rev $GIT_VER" \
    --define "_topdir $TOPDIR" --define "product_family $PRODUCT_FAMILY" -bb $TMPDIR/sspl_cli.spec
fi

if [ "$TEST" == true ]
then
    rpmbuild --define "version $VERSION" --define "git_rev $GIT_VER" \
        --define "_topdir $TOPDIR" --define "product_family $PRODUCT_FAMILY" -bb $TMPDIR/sspl-test.spec
fi
echo "Generated rpm's for sspl build"

BUILD_END_TIME=$(date +%s)
# cleanup
\rm -rf $TMPDIR
\rm -rf $DIST/sspl
\rm -rf $DIST/sspl_test
\rm -rf $DIST/cli
# remove systemd-python36
yum erase -y systemd-python36-*

echo -e "\nGenerated RPMs..."
find $RPM_BUILD_PATH -name "*.rpm"
