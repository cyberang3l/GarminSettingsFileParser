.PHONY: clean clean-all unittests unittests-verbose

all: unittests

unittests:
	@# Search for python files that end in *_test.py and run the unit test.
	@# Only works if the directory contains the __init__.py file
	@python3 -m unittest discover -p *_test.py -v -s tests -b

unittests-verbose:
	@# Search for python files that end in *_test.py and run the unit test.
	@# Only works if the directory contains the __init__.py file
	@python3 -m unittest discover -p *_test.py -v -s tests

clean:
	find . -name '*.pyc' -type f -delete
	find . -name __pycache__ -type d -delete
	git clean -fd

clean-all:
	git clean -ffdx
