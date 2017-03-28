AUTOMAKE_OPTIONS=foreign
SUBDIRS=libsspl_sec doc tests
STYLECHECKER=$(ASTYLE) --style=ansi --attach-extern-c --indent-classes --indent-switches --break-blocks --pad-oper --pad-header --unpad-paren --align-pointer=type --remove-brackets --convert-tabs --max-code-length=80  --lineend=linux | head -n-1

if HAVE_LCOV
cov:
	$(MAKE) -C doc cov_init
	$(MAKE) check
	$(MAKE) -C doc cov_fini
else
cov:
	@echo "Coverage testing disabled"
endif

.PHONY: sspl-$(PACKAGE_VERSION).tgz
sspl-$(PACKAGE_VERSION).tgz:
	rm -rf $(top_builddir)/RPMBUILD
	mkdir --parents $(top_builddir)/RPMBUILD/SOURCES
	mkdir --parents $(top_builddir)/RPMBUILD/results
	(cd .. && \
	git archive --format=tar --prefix=sspl/ HEAD . | gzip > $(abs_top_builddir)/RPMBUILD/SOURCES/sspl-$(PACKAGE_VERSION).tgz)

.PHONY: rpm
rpm: sspl-$(PACKAGE_VERSION).tgz libsspl_sec.spec
	rpmbuild --define "_topdir $(abs_top_builddir)/RPMBUILD" --define "_tmppath $(abs_top_builddir)/RPMBUILD/tmp/" -ba libsspl_sec.spec

check-local: c_style 

if HAVE_ASTYLE
c_style:
	@rm -f stylecheck.tmp
	@for file in `find $(top_srcdir) -name '*.h' -or -name '*.c'` ; do \
		cat $$file | $(STYLECHECKER) > stylecheck.tmp ; \
		if ! diff -q $$file stylecheck.tmp > /dev/null ; then \
			echo "ERROR $$file failed style check." ; \
			echo "Hint: vimdiff $$file stylecheck.tmp" ; \
			exit 1 ; \
		fi ; \
	done
else
c_style:
	@echo "C style checking disabled"
endif

c_style_interactive:
	@rm -f stylecheck.tmp
	@for file in `find $(top_srcdir) -name '*.h' -or -name '*.c'` ; do \
		cat $$file | $(STYLECHECKER) > stylecheck.tmp ; \
		if ! diff -q $$file stylecheck.tmp > /dev/null ; then \
			vimdiff $$file stylecheck.tmp ; \
		fi ; \
	done

clean-local:
	rm -rf RPMBUILD

EXTRA_DIST=libsspl_sec.spec
MOSTLYCLEANFILES=*.gcno *.gcda stylecheck.tmp
