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

AM_CFLAGS=-I$(top_srcdir)/libsspl_sec $(CHECK_CFLAGS)
LDADD=$(top_builddir)/libsspl_sec/libsspl_sec.la $(CHECK_LIBS)

check_PROGRAMS=test_sec_method test_none test_pki

test_sec_method_SOURCES=test_sec_method.c
test_sec_method_LDFLAGS=-ldl
test_none_SOURCES=test_none.c
test_pki_SOURCES=test_pki.c

TESTS=$(check_PROGRAMS)
MOSTLYCLEANFILES=*.gcno *.gcda
