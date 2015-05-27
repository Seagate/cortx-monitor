all: docs

.PHONY: docs
docs: Doxyfile
	$(DOXYGEN)

clean-local:
	rm -rf html latex doxygen_sqlite3.db
