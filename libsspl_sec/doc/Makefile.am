AUTOMAKE_OPTIONS=subdir-objects
AM_CFLAGS=-I$(top_srcdir)/libsspl_sec
LDADD=$(top_builddir)/libsspl_sec/libsspl_sec.la

noinst_PROGRAMS=01_message_creator 02_message_consumer
01_message_creator_SOURCES=./examples/c/01_message_creator.c
02_message_consumer_SOURCES=./examples/c/02_message_consumer.c

all-local: docs

if HAVE_LCOV
cov_init:
	find .. -name *.gcda -exec rm '{}' \;
	mkdir -p lcov
	$(LCOV) --rc lcov_branch_coverage=1 --directory ../libsspl_sec --capture --initial --output-file ./lcov/libsspl_sec.base.info

cov_fini:
	mkdir -p lcov
	$(LCOV) --rc lcov_branch_coverage=1 --directory ../libsspl_sec --base-directory=../libsspl_sec --capture --output-file ./lcov/libsspl_sec.test.info
	$(LCOV) --rc lcov_branch_coverage=1 -a ./lcov/libsspl_sec.base.info -a ./lcov/libsspl_sec.test.info -o ./lcov/tests.info
	$(LCOV) --rc lcov_branch_coverage=1 -o ./lcov/tests.info -r ./lcov/tests.info '/usr/include/*'
	$(GENHTML) --branch-coverage --rc lcov_branch_coverage=1 --output-directory=./lcov ./lcov/tests.info
else
cov_init cov_fini:
	@echo "Coverage testing not enabled"
endif

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
	rm -rf html latex
	find . -name '*.gcno' -exec rm '{}' \;
	find . -name '*.gcda' -exec rm '{}' \;

EXTRA_DIST=Doxyfile ./examples/python/01_message_creator.py
MOSTLYCLEANFILES=doxygen_sqlite3.db
