AUTOMAKE_OPTIONS=foreign
SUBDIRS=libsspl_sec doc tests
STYLECHECKER=$(ASTYLE) --style=ansi --attach-extern-c --indent-classes --indent-switches --break-blocks --pad-oper --pad-header --unpad-paren --align-pointer=type --remove-brackets --convert-tabs --max-code-length=80  --lineend=linux | head -n-1

.PHONY: rpm
rpm: dist libsspl_sec.spec
	rm -rf $(top_builddir)/rpmbuild
	mkdir -p $(top_builddir)/rpmbuild/BUILD $(top_builddir)/rpmbuild/BUILDROOT $(top_builddir)/rpmbuild/RPMS $(top_builddir)/rpmbuild/SOURCES $(top_builddir)/rpmbuild/SPECS $(top_builddir)/rpmbuild/SRPMS $(top_builddir)/rpmbuild/tmp
	cp ${PACKAGE}-${VERSION}.tar.gz $(top_builddir)/rpmbuild/SOURCES
	rpmbuild --define "_topdir $(abs_top_builddir)/rpmbuild" --define "_tmppath $(abs_top_builddir)/rpmbuild/tmp/" -ba libsspl_sec.spec

check-local: c_style python_style

python_style:
	$(FLAKE8) $(top_srcdir)
	$(PYLINT) --module-rgx='.*' $(top_srcdir)/doc/examples/python/*.py
	$(PYLINT) $(top_srcdir)/tests/acceptance/steps/*.py

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
	rm -f stylecheck.tmp

EXTRA_DIST=libsspl_sec.spec
