#!/usr/bin/python
# -*- coding: utf-8 -*-


import os
import re

from setuptools import setup


def read_module_contents():
    with open('productmd/__init__.py') as installer_init:
        return installer_init.read()

module_file = read_module_contents()
metadata = dict(re.findall("__([a-z]+)__\s*=\s*'([^']+)'", module_file))
version = metadata['version']
long_description = open('README.rst').read()


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
    version         = version,
    description     = "Product, compose and installation media metadata library",
    url             = "https://github.com/release-engineering/productmd",
    author          = "Daniel Mach",
    author_email    = "dmach@redhat.com",
    long_description=long_description,
    license         = "LGPLv2.1",

    packages        = packages,
    scripts         = [],
    test_suite      = "tests",
    install_requires=[
        'six',
    ],
)
