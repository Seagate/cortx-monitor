SUBDIRS=helpers
check-local:
	$(MAKE) -C helpers
	$(LETTUCE) $(srcdir)

EXTRA_DIST=$(srcdir)/*.feature $(srcdir)/steps/*.py
