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
