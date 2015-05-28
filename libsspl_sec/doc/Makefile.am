AUTOMAKE_OPTIONS=subdir-objects
AM_CFLAGS=-I$(top_srcdir)/libsspl_sec
LDADD=$(top_builddir)/libsspl_sec/libsspl_sec.la

noinst_PROGRAMS=01_message_creator 02_message_consumer
01_message_creator_SOURCES=./examples/c/01_message_creator.c
02_message_consumer_SOURCES=./examples/c/02_message_consumer.c

all-local: docs

.PHONY: docs
docs: Doxyfile
	$(DOXYGEN)


clean-local:
	rm -rf html latex doxygen_sqlite3.db
