AM_CFLAGS=-I$(top_srcdir)/libsspl_sec $(CHECK_CFLAGS)
LDADD=$(top_builddir)/libsspl_sec/libsspl_sec.la $(CHECK_LIBS)

check_PROGRAMS=test_sec_method test_none test_pki

test_sec_method_SOURCES=test_sec_method.c
test_sec_method_LDFLAGS=-ldl
test_none_SOURCES=test_none.c
test_pki_SOURCES=test_pki.c

TESTS=$(check_PROGRAMS)
MOSTLYCLEANFILES=*.gcno *.gcda
