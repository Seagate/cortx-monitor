NAME=sspl_hl
VERSION=1.0.0
RELEASE=1.el7

MOCK_CONFIG=-r mock_osaint

.PHONY: check pep8 pylint ut at
check: pep8 pylint ut at

at:
	PYTHONPATH=.:tests lettuce --failfast ./tests/acceptance/power_request.feature
	PYTHONPATH=.:tests lettuce --failfast ./tests/acceptance/bundle_request.feature
	PYTHONPATH=.:tests lettuce --failfast ./tests/acceptance/status_request.feature

ut:
	PYTHONPATH=.:tests python tests/unit/sspl_hl_provider_power.py
	PYTHONPATH=.:tests python tests/unit/sspl_hl_provider_supportbundle.py
	PYTHONPATH=.:tests python tests/unit/sspl_hl_provider_status.py

pep8:
	pep8 ./sspl_hl ./cstor ./tests/

pylint:
	PYTHONPATH=.:tests pylint \
		--disable=locally-disabled,locally-enabled \
		--rcfile=pylint.rc \
		./sspl_hl \
		./cstor \
		./tests/fake_halond/fake_halond.py \
		./tests/acceptance/steps/*.py \
		./tests/unit/*.py

.PHONY: tarball
tarball:
	rm -rf RPMBUILD
	mkdir --parents RPMBUILD/SOURCES
	mkdir --parents RPMBUILD/results
	(cd .. && \
	git archive --format=tar --prefix=sspl/ HEAD . | gzip > high-level/RPMBUILD/SOURCES/sspl-$(VERSION).tgz)

.PHONY: native
native: tarball sspl_hl.spec
	rpmbuild --define '_topdir $(shell pwd)/RPMBUILD' -ba sspl_hl.spec


$(NAME)-$(VERSION)-$(RELEASE).src.rpm: tarball sspl_hl.spec
	mock $(MOCK_CONFIG) --buildsrpm --spec sspl_hl.spec --sources RPMBUILD/SOURCES --resultdir RPMBUILD/result
	cp RPMBUILD/result/$@ .

$(NAME)-$(VERSION)-$(RELEASE).noarch.rpm: $(NAME)-$(VERSION)-$(RELEASE).src.rpm
	mock $(MOCK_CONFIG) --resultdir RPMBUILD/result --rebuild $<
	cp RPMBUILD/result/$@ .
	#python2.7 setup.py bdist_rpm
	#cp dist/*.rpm .

.PHONY: mock
mock: $(NAME)-$(VERSION)-$(RELEASE).noarch.rpm

.PHONY: rpm
rpm: native

clean:
	rm -f $(NAME)-*.rpm
	rm -rf RPMBUILD

