AUTOMAKE_OPTIONS=subdir-objects
AM_CFLAGS=-I$(top_srcdir)/libsspl_sec
LDADD=$(top_builddir)/libsspl_sec/libsspl_sec.la

noinst_PROGRAMS=01_message_creator 02_message_consumer
01_message_creator_SOURCES=./examples/c/01_message_creator.c
02_message_consumer_SOURCES=./examples/c/02_message_consumer.c

all-local: docs

.PHONY: docs
docs: Doxyfile
	$(DOXYGEN) $(srcdir)/Doxyfile

install-data-local:
	$(MKDIR_P) $(DESTDIR)$(docdir)/html
	for f in `ls $(builddir)/html` ; do \
		$(INSTALL_DATA) $(builddir)/html/$$f \
			$(DESTDIR)$(docdir)/html; \
	done

uninstall-local:
	rm $(DESTDIR)$(docdir)/html/*
	-rmdir $(DESTDIR)$(docdir)/html

clean-local:
	rm -rf html latex doxygen_sqlite3.db

EXTRA_DIST=Doxyfile ./examples/python/01_message_creator.py
