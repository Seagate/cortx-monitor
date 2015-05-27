#!/bin/sh

set -e

if [ -e Makefile ] ; then
    make clean
fi

rm -rf aclocal.m4 autom4te.cache compile config.guess config.sub configure install-sh ltmain.sh missing
