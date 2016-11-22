.PHONY: all clean doc log test


all: help


help:
	@echo "Usage: make <target>"
	@echo
	@echo "Available targets are:"
	@echo " help                    show this text"
	@echo " clean                   remove python bytecode and temp files"
	@echo " doc                     build documentation"
	@echo " install                 install program on current system"
	@echo " log                     prepare changelog for spec file"
	@echo " rpm                     create a *test* rpm with tito"
	@echo " source                  create source tarball"
	@echo
	@echo " test                    run ./setup.py test"
	@echo " flake8                  run flake8"
	@echo " pylint                  run pylint"


clean:
	@python setup.py clean
	rm -f MANIFEST
	find . -\( -name "*.pyc" -o -name '*.pyo' -o -name "*~" -o -name "__pycache__" -\) -delete
	find . -depth -type d -a -name '*.egg-info' -exec rm -rf {} \;


install:
	@python setup.py install


doc:
	cd doc; make html && make man


log:
	@(LC_ALL=C date +"* %a %b %e %Y `git config --get user.name` <`git config --get user.email`> - VERSION"; git log --pretty="format:- %s (%an)" | cat) | less


rpm:
	@tito build --rpm --offline --test


source:
	@./setup-sdist-wrapper.sh


test:
	python2 setup.py test
	python3 setup.py test


flake8:
	flake8 --config=tox.ini productmd tests
	python3-flake8 --config=tox.ini productmd tests


pylint:
	pylint --max-line-length=140 productmd tests
	python3-pylint --max-line-length=140 productmd tests
