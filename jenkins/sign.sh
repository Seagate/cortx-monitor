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

default_name="Seagate SSPL RAS"
default_email="CORTX.ras@seagate.com"
default_comment="LDR_R1 RAS SSPL developer RPM signing key"

if [ "$#" -eq 0 ]; then
    key_name="${default_name}"
    key_email="${default_email}"
    key_comment="${default_comment}"
elif [ "$#" -eq 3 ]; then
    key_name="$1"
    key_email="$2"
    key_comment="$3"
else
    1>&2 echo "Error: Unexpected number of arguments: $#"
    1>&2 echo "Usage:"
    1>&2 echo "${0}"
    1>&2 echo "OR"
    1>&2 echo "${0} <key-name> <key-email> <key-comment>"
    exit 1
fi

if [ '!' -f ~/.rpmmacros ]; then
    cp ./jenkins/rpmmacros ~/.rpmmacros
fi

./jenkins/sign_rpms "${key_name}" "${key_email}" "${key_comment}" \
    $(find ~/rpmbuild -name "*.rpm")

