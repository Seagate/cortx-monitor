#!/bin/bash

set -e

BUILD_START_TIME=$(date +%s)
BASE_DIR=$(realpath $(dirname $0)/..)

PROG_NAME=$(basename $0)
DIST=$(realpath $BASE_DIR/dist)

usage() {
    echo "usage: $PROG_NAME [-g <git version>] [-v <sspl version>] [-k <key>]
                            [-p <product_name>] [-t <true|false>]" 1>&2;
    exit 1;
}

while getopts ":g:v:p:k:t" o; do
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
        *)
            usage
            ;;
    esac
done

cd $BASE_DIR
[ -z "$GIT_VER" ] && GIT_VER=$(git rev-parse --short HEAD)
[ -z "$VERSION" ] && VERSION=$(cat $BASE_DIR/VERSION)

#product and key for sspl pyinstaller
[ -z "$PRODUCT" ] && PRODUCT="eos"
[ -z "$KEY" ] && KEY="eos@ees@sspl@pr0duct"
[ -z "$TEST" ] && TEST=true

echo "Using VERSION=${VERSION} GIT_VER=${GIT_VER} PRODUCT=${PRODUCT} TEST=${TEST} "

################### COPY FRESH DIR ##############################
COPY_START_TIME=$(date +%s)
DIST="$BASE_DIR/dist"
TMPDIR="$DIST/tmp"

[ -d "$TMPDIR" ] && {
    rm -rf ${TMPDIR}
}
mkdir -p $DIST/sspl/bin $DIST/sspl/conf $DIST/sspl/resources/actuators $DIST/sspl/resources/actuator_msgs $DIST/sspl/resources/sensors $TMPDIR

cp -R $BASE_DIR/low-level/snmp $DIST/sspl/conf
cp -R $BASE_DIR/low-level/files/opt/seagate/sspl/bin/* $DIST/sspl/bin
cp -R $BASE_DIR/low-level/requirements.txt $DIST/sspl/conf/requirements.txt
cp -R $BASE_DIR/low-level/framework/base/sspl_constants.py $DIST/sspl/bin/sspl_constants.py
cp -R $BASE_DIR/low-level/framework/base/sspl_conf_adopt.py $DIST/sspl/bin/sspl_conf_adopt.py
cp -R $BASE_DIR/low-level/framework/sspl_init $DIST/sspl/bin
cp -R $BASE_DIR/low-level/framework/sspl_reinit $DIST/sspl/bin
cp -R $BASE_DIR/low-level/framework/sspl_rabbitmq_reinit $DIST/sspl/bin

cp -R $BASE_DIR/low-level/json_msgs/schemas/actuators/*.json $DIST/sspl/resources/actuators
cp -R $BASE_DIR/low-level/json_msgs/schemas/sensors/*.json $DIST/sspl/resources/sensors
cp -R $BASE_DIR/low-level/tests/manual/actuator_msgs/*.json $DIST/sspl/resources/actuator_msgs
cp -R $BASE_DIR/low-level/tests/manual/actuator_msgs/*.conf $DIST/sspl/resources/actuator_msgs

cp -R $BASE_DIR/libsspl_sec/ $DIST/sspl
cp -R $BASE_DIR/systemd-python36/ $DIST/sspl

CONF=$BASE_DIR/low-level/files
cp -R $CONF/opt/seagate/sspl/conf/* $CONF/etc $DIST/sspl/conf
cp $BASE_DIR/low-level/sspl-ll.spec $TMPDIR
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

if [ "$TEST" == true ]
then
    mkdir -p $TMPDIR/sspl_test $DIST/sspl_test $DIST/sspl_test/conf
    cp -R $BASE_DIR/sspl_test/* $TMPDIR/sspl_test
    PYINSTALLER_FILE=$TMPDIR/${PRODUCT}_sspl_test.spec
    cp $BASE_DIR/jenkins/pyinstaller/run_test.spec ${PYINSTALLER_FILE}
    cp -R $BASE_DIR/sspl_test/mock_data $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/plans $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/run_tests.sh $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/run_qa_test.sh $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/run_sspl-ll_tests.sh $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/set_threshold.sh $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/mock_server $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/rabbitmq_start_checker $DIST/sspl_test
    cp -R $BASE_DIR/sspl_test/sspl_tests.conf $DIST/sspl_test/conf

    echo "Executing pyinstaller..."
    sed -i -e "s|<PRODUCT>|${PRODUCT}|g" \
            -e "s|<SSPL_TEST_PATH>|${TMPDIR}/sspl_test|g" \
            -e "s|<SSPL_PATH>|${TMPDIR}/sspl|g" ${PYINSTALLER_FILE}
    python3 -m PyInstaller --clean -y --distpath ${DIST}/sspl_test --key ${KEY} ${PYINSTALLER_FILE}
fi

python3 -m pip install --user -r $req_file  > /dev/null || {
    echo "Unable to install package from $req_file"; exit 1;
};
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
cd $BASE_DIR
rm -rf ${DIST}/rpmbuild
mkdir -p ${DIST}/rpmbuild/SOURCES

# Create tar for sspl
echo "Creating tar for sspl build"

if [ "$TEST" == true ]
then
    tar -czvf ${DIST}/rpmbuild/SOURCES/sspl-test-${VERSION}.tgz -C ${DIST} sspl_test
fi

tar -czvf ${DIST}/rpmbuild/SOURCES/sspl-${VERSION}.tgz -C ${DIST} sspl
tar -czvf ${DIST}/rpmbuild/SOURCES/systemd-python36-${VERSION}.tgz -C ${DIST} sspl

TAR_END_TIME=$(date +%s)
echo "Generated tar for sspl build"

################### RPM builds for SSPL ##############################
echo "Generating rpm's for sspl build"
RPM_BUILD_START_TIME=$(date +%s)
TOPDIR=$(realpath ${DIST}/rpmbuild)
echo $TOPDIR

rpmbuild --define "version $VERSION" --define "git_rev $GIT_VER" --define "_topdir $TOPDIR" -bb $TMPDIR/sspl-ll.spec
rpmbuild --define "version $VERSION" --define "git_rev $GIT_VER" --define "_topdir $TOPDIR" -bb $TMPDIR/libsspl_sec.spec
rpmbuild --define "version $VERSION" --define "git_rev $GIT_VER" --define "_topdir $TOPDIR" -bb $TMPDIR/systemd-python36.spec

if [ "$TEST" == true ]
then
    rpmbuild --define "version $VERSION" --define "git_rev $GIT_VER" --define "_topdir $TOPDIR" -bb $TMPDIR/sspl-test.spec
fi
echo "Generated rpm's for sspl build"

BUILD_END_TIME=$(date +%s)
# cleanup
\rm -rf $TMPDIR
\rm -rf $DIST/sspl
\rm -rf $DIST/sspl_test
echo -e "\nGenerated RPMs..."
find $DIST -name "*.rpm"