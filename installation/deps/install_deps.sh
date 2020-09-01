#!/bin/bash -x

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

FEDORA_21_BASE_URL="https://archive.fedoraproject.org/pub/archive/fedora/linux/releases/21/Everything/x86_64/os/Packages/p"
FEDORA_22_BASE_URL="https://archive.fedoraproject.org/pub/archive/fedora/linux/releases/22/Everything/x86_64/os/Packages/p"
fedora_deps="$FEDORA_21_BASE_URL/python-ldaptor-0.0.44-6.20140909gitc30f30d9.fc21.noarch.rpm $FEDORA_21_BASE_URL/python-twisted-names-12.2.0-4.fc21.x86_64.rpm $FEDORA_21_BASE_URL/python-twisted-mail-12.2.0-4.fc21.x86_64.rpm  $FEDORA_21_BASE_URL/python-lettuce-0.2.19-2.fc21.noarch.rpm $FEDORA_21_BASE_URL/python-pep8-1.5.6-3.fc21.noarch.rpm $FEDORA_22_BASE_URL/python-characteristic-14.3.0-1.fc22.noarch.rpm $FEDORA_22_BASE_URL/python-service-identity-14.0.0-1.fc22.noarch.rpm $FEDORA_22_BASE_URL/python-fuzzywuzzy-0.5.0-1.fc22.noarch.rpm"

yum install -y 		\
python-sure		\
lksctp-tools		\
net-snmp-libs		\
openhpi			\
pysnmp			\
openhpi-libs		\
python-ldap             \
openldap-clients        \
openldap-servers        \
python-daemon		\
python-inotify		\
python-jsonschema	\
python-lockfile		\
python-pika		\
python-zope-interface	\
python-zope-component	\
python-paramiko         \
python-psutil           \
pyserial                \
libsspl_sec             \
pylint                  \
dbus-python             \
systemd-python          \
pygobject2              \
automake                \
autoconf                \
libtool                 \
doxygen                 \
check                 \
check-devel                 \
openssl-devel                 \
rpm-build                 \
graphviz                 \
git                 \
$fedora_deps
