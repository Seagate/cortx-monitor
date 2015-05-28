AUTOMAKE_OPTIONS=foreign
SUBDIRS=libsspl_sec doc tests
STYLECHECKER=$(ASTYLE) --style=ansi --attach-extern-c --indent-classes --indent-switches --break-blocks --pad-oper --pad-header --unpad-paren --align-pointer=type --remove-brackets --convert-tabs --max-code-length=80  --lineend=linux | head -n-1

check-local: c_style python_style

python_style:
	$(FLAKE8) .
	$(PYLINT) --module-rgx='.*' ./doc/examples/python/*.py
	$(PYLINT) ./tests/acceptance/steps/*.py

c_style:
	@echo ">>> $(STYLECHECKER) <<<"
	@rm -f stylecheck.tmp
	@for file in `find . -name '*.h' -or -name '*.c'` ; do \
		cat $$file | $(STYLECHECKER) > stylecheck.tmp ; \
		if ! diff -q $$file stylecheck.tmp > /dev/null ; then \
			echo "ERROR $$file failed style check." ; \
			echo "Hint: vimdiff $$file stylecheck.tmp" ; \
			exit 1 ; \
		fi ; \
	done

c_style_interactive:
	@rm -f stylecheck.tmp
	@for file in `find . -name '*.h' -or -name '*.c'` ; do \
		cat $$file | $(STYLECHECKER) > stylecheck.tmp ; \
		if ! diff -q $$file stylecheck.tmp > /dev/null ; then \
			vimdiff $$file stylecheck.tmp ; \
		fi ; \
	done

clean-local:
	rm -f stylecheck.tmp

