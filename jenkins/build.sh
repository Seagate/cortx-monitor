#!/bin/bash

set -e

BASE_DIR=$(realpath $(dirname $0)/..)
cd $BASE_DIR
PROG_NAME=$(basename $0)
DIST=${DIST:-$HOME/rpmbuild}

usage() {
    echo "usage: $PROG_NAME [-g <git version>] [-v <sspl version>]" 1>&2;
    exit 1;
}

while getopts ":g:v:" o; do
    case "${o}" in
        g)
            GIT_VER=${OPTARG}
            ;;
        v)
            VERSION=${OPTARG}
            ;;
        *)
            usage
            ;;
    esac
done

[ -z "$GIT_VER" ] && GIT_VER=$(git rev-parse --short HEAD)
[ -z "$VERSION" ] && VERSION=$(cat $BASE_DIR/VERSION)

echo "Using [VERSION=${VERSION}] ..."
echo "Using [GIT_VER=${GIT_VER}] ..."

# Remove existing directory tree and create fresh one.
rm -rf $DIST/
mkdir -p $DIST/SOURCES

# Create tar of source directory
tar -czvf $DIST/SOURCES/sspl-$VERSION.tgz -C $BASE_DIR/.. sspl/low-level sspl/libsspl_sec
tar -czvf $DIST/SOURCES/sspl-test-lettuce-py2.7-$VERSION.tgz -C $BASE_DIR/.. sspl/test
tar -czvf $DIST/SOURCES/sspl-test-$VERSION.tgz -C $BASE_DIR/.. sspl/sspl_test
tar -czvf $DIST/SOURCES/systemd-python36-$VERSION.tgz -C $BASE_DIR/.. sspl/systemd-python36

# Generate RPMs
rpmbuild --define "version $VERSION" --define "git_rev $GIT_VER" --define "_topdir $DIST" -bb $BASE_DIR/low-level/sspl-ll.spec
rpmbuild --define "version $VERSION" --define "git_rev $GIT_VER" --define "_topdir $DIST" -bb $BASE_DIR/libsspl_sec/libsspl_sec.spec
rpmbuild --define "version $VERSION" --define "git_rev $GIT_VER" --define "_topdir $DIST" -bb $BASE_DIR/test/sspl-test.spec
rpmbuild --define "version $VERSION" --define "git_rev $GIT_VER" --define "_topdir $DIST" -bb $BASE_DIR/sspl_test/sspl-test-ctf.spec
rpmbuild --define "version $VERSION" --define "git_rev $GIT_VER" --define "_topdir $DIST" -bb $BASE_DIR/systemd-python36/systemd-python36.spec

\rm -rf $DIST/BUILD/*
echo -e "\nGenerated RPMs..."
find $DIST -name "*.rpm"
