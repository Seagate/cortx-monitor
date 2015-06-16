AM_CFLAGS=-I$(top_srcdir)/libsspl_sec $(CHECK_CFLAGS)
LDADD=$(top_builddir)/libsspl_sec/libsspl_sec.la $(CHECK_LIBS)

check_PROGRAMS=test_sec

test_sec_SOURCES=test_sec.c

TESTS=$(check_PROGRAMS)
MOSTLYCLEANFILES=*.gcno *.gcda
