NAME=sspl_hl
VERSION=0.0.1
RELEASE=1.el7.centos

check: pep8 pylint ut at

at:
	PYTHONPATH=. lettuce --failfast ./tests/acceptance/*.feature

ut:
	PYTHONPATH=. python tests/unit/sspl_hl_provider_service.py

pep8:
	pep8 ./sspl_hl ./cli ./tests/

pylint:
	pylint \
		--disable=locally-disabled,locally-enabled \
		--rcfile=pylint.rc \
		./sspl_hl \
		./cli \
		./tests/fake_halond/fake_halond.py \
		./tests/acceptance/steps/*.py

$(NAME)-$(VERSION).tar.gz:
	cd .. && git archive --format=tar --prefix=$(NAME)-$(VERSION)/ HEAD:high-level | gzip > high-level/$(NAME)-$(VERSION).tar.gz

$(NAME)-$(VERSION)-$(RELEASE).src.rpm: sspl_hl.spec $(NAME)-$(VERSION).tar.gz
	mock --buildsrpm --spec sspl_hl.spec --sources $(NAME)-$(VERSION).tar.gz
	cp /var/lib/mock/epel-7-x86_64/result/$@ .

$(NAME)-$(VERSION)-$(RELEASE).noarch.rpm: $(NAME)-$(VERSION)-$(RELEASE).src.rpm
	mock --rebuild $<
	cp /var/lib/mock/epel-7-x86_64/result/$@ .
	#python2.7 setup.py bdist_rpm
	#cp dist/*.rpm .

.PHONY: rpm
rpm: $(NAME)-$(VERSION)-$(RELEASE).noarch.rpm

clean:
	rm $(NAME)-*.rpm $(NAME)-*.tar.gz
