#!/usr/bin/python
# -*- coding: utf-8 -*-


import os

import distutils.command.sdist
from setuptools import setup


# override default tarball format with bzip2
distutils.command.sdist.sdist.default_format = {"posix": "bztar"}


# recursively scan for python modules to be included
package_root_dirs = ["productmd"]
packages = set()
for package_root_dir in package_root_dirs:
    for root, dirs, files in os.walk(package_root_dir):
        if "__init__.py" in files:
            packages.add(root.replace("/", "."))
packages = sorted(packages)


setup(
    name            = "productmd",
    version         = "1.2",
    description     = "Product, compose and installation media metadata library",
    url             = "https://github.com/release-engineering/productmd",
    author          = "Daniel Mach",
    author_email    = "dmach@redhat.com",
    license         = "LGPLv2.1",

    packages        = packages,
    scripts         = [],
    test_suite      = "tests",
)
