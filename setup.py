#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import re

from setuptools import setup


# Read version from pyproject.toml
def get_version():
    here = os.path.abspath(os.path.dirname(__file__))
    pyproject_path = os.path.join(here, "pyproject.toml")
    with open(pyproject_path, "r") as f:
        content = f.read()
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    if match:
        return match.group(1)
    raise RuntimeError("Unable to find version in pyproject.toml")


# recursively scan for python modules to be included
package_root_dirs = ["productmd"]
packages = set()
for package_root_dir in package_root_dirs:
    for root, dirs, files in os.walk(package_root_dir):
        if "__init__.py" in files:
            packages.add(root.replace("/", "."))
packages = sorted(packages)


setup(
    name="productmd",
    version=get_version(),
    description="Product, compose and installation media metadata library",
    url="https://github.com/release-engineering/productmd",
    author="Daniel Mach",
    author_email="dmach@redhat.com",
    license="LGPLv2.1",
    packages=packages,
    scripts=[],
    test_suite="tests",
)
