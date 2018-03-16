#!/bin/bash -x

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
