check: pep8 pylint ut at

at:
	lettuce --failfast ./tests/acceptance/*.feature

ut:
	PYTHONPATH=. python tests/unit/sspl_hl_provider_service.py

pep8:
	pep8 ./sspl_hl ./tests/

pylint:
	pylint \
		--disable=locally-disabled \
		--rcfile=pylint.rc \
		./sspl_hl \
		./tests/fake_halond/fake_halond.py \
		./tests/acceptance/steps/*.py
