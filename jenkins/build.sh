#!/bin/bash

set -e

BASE_DIR=$(realpath $(dirname $0)/..)
cd $BASE_DIR
PROG_NAME=$(basename $0)
DIST=$(realpath $BASE_DIR/dist)

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
\rm -rf $DIST/rpmbuild
mkdir -p $DIST/rpmbuild/SOURCES

# Create tar of source directory
tar -czvf $DIST/rpmbuild/SOURCES/sspl-$VERSION.tgz -C $BASE_DIR/.. sspl/low-level sspl/libsspl_sec

# Generate RPMs
rpmbuild --define "version $VERSION" --define "dist $GIT_VER" --define "_topdir $DIST/rpmbuild" -bb $BASE_DIR/low-level/sspl-ll.spec
rpmbuild --define "version $VERSION" --define "dist $GIT_VER" --define "_topdir $DIST/rpmbuild" -bb $BASE_DIR/libsspl_sec/libsspl_sec.spec

\rm -rf $DIST/rpmbuild/BUILD/*
echo -e "\nGenerated RPMs..."
find $DIST -name "*.rpm"
