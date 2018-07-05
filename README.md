ProductMD
=========

[![Build Status](https://travis-ci.org/release-engineering/productmd.svg?branch=master)](https://travis-ci.org/release-engineering/productmd)
[![Documentation Status](https://readthedocs.org/projects/productmd/badge/?version=latest)](http://productmd.readthedocs.io/en/latest/?badge=latest)

ProductMD is a Python library providing parsers for metadata related to composes and installation media.


Documentation
-------------

http://productmd.readthedocs.io/en/latest/


Building
--------

### Build requires

* Six: Python 2 and 3 Compatibility Library
 * `pip install six`
 * Fedora: `dnf install python-six python3-six`


### Build

To see all options run:

    make help


### Build with Tito

Read [TITO.md](TITO.md) for instructions.


Testing
-------

Run from checkout dir:

    make test


