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

lib_LTLIBRARIES=libsspl_sec.la
pkglib_LTLIBRARIES=sspl_none.la sspl_pki.la
include_HEADERS=sspl_sec.h
noinst_HEADERS=sec_method.h

libsspl_sec_la_SOURCES=sec.c sec_method.c
libsspl_sec_la_LDFLAGS=--version-info 0:0:0 -R=$(libdir)/libsspl_sec/
libsspl_sec_la_LIBADD=-ldl

sspl_none_la_SOURCES=none.c
sspl_none_la_LDFLAGS=-module

sspl_pki_la_SOURCES=pki.c
sspl_pki_la_LDFLAGS=-module -lcrypto
sspl_pki_la_LIBADD=-lcrypto

MOSTLYCLEANFILES=*.gcno *.gcda
