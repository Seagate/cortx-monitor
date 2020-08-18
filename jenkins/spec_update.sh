#!/bin/bash -xv

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

# Modify Spec file

[ $# -ne 7 ] && echo "Usage: " && exit 1

name=$1
version=$2
url=$3
repo_dir=$4
RPMBLDDIR=$5
BUILD_NUMBER=$6
SRCSPECFILE=$7

SRCSPECFILE=${SRCSPECFILE:-${repo_dir}/${name}.spec}
RPMSPECFILE=${RPMBLDDIR}/SPECS/${name}.spec

sed -e '/#xyr build defines/,/#xyr end defines/d'  ${SRCSPECFILE} > ${RPMSPECFILE}.in

echo "#xyr build defines" > ${RPMSPECFILE}
echo "%define _xyr_package_name     ${name}" >> ${RPMSPECFILE}
echo "%define _xyr_package_source   ${name}.tgz" >>  ${RPMSPECFILE}
echo "%define _xyr_package_version  ${version}" >>  ${RPMSPECFILE}
echo "%define _xyr_build_number     ${BUILD_NUMBER}" >>  ${RPMSPECFILE}

if [ ! -z "${url}" ] ; then
     echo "%define _xyr_pkg_url          ${url}" >> ${RPMSPECFILE}
fi
if [ -d ${repo_dir}/.git ] ; then
    svn_ver=$(git rev-list --max-count=1 HEAD | cut -c1-8)
fi
if [ -d ${repo_dir}/.svn ] ; then
    svn_ver=$(svn info ${repo_dir} 2>/dev/null | grep "Revision:" | cut -f2 -d" ")
fi

if [ ! -z "${svn_ver}" ] ; then
   echo "%define _xyr_svn_version      ${svn_ver}" >> ${RPMSPECFILE}
fi

echo "#xyr end defines" >> ${RPMSPECFILE}

cat ${RPMSPECFILE}.in >> ${RPMSPECFILE}
rm ${RPMSPECFILE}.in

