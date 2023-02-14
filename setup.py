#!/usr/bin/python
# -*- coding: utf-8 -*-


import os

from setuptools import setup


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
    version         = "1.34",
    description     = "Product, compose and installation media metadata library",
    url             = "https://github.com/release-engineering/productmd",
    author          = "Daniel Mach",
    author_email    = "dmach@redhat.com",
    license         = "LGPLv2.1",

    packages        = packages,
    scripts         = [],
    test_suite      = "tests",
    install_requires=[
        'six',
    ],
)
