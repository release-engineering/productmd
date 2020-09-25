#!/usr/bin/python
# -*- coding: utf-8 -*-


# Copyright (C) 2015  Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA


import unittest

import os
import sys
import tempfile
import shutil

DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(DIR, ".."))

from productmd.composeinfo import ComposeInfo, Variant, Release, get_date_type_respin  # noqa


class TestComposeInfo(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestComposeInfo, self).__init__(*args, **kwargs)
        self.treeinfo_path = os.path.join(DIR, "treeinfo")

    def setUp(self):
        self.maxDiff = None
        self.tmp_dir = tempfile.mkdtemp()
        self.ci_path = os.path.join(self.tmp_dir, "composeinfo")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def assertSameFiles(self, path1, path2):
        self.assertEqual(os.path.getsize(path1), os.path.getsize(path2))
        with open(path1, "r") as file1:
            with open(path2, "r") as file2:
                self.assertEqual(file1.read(), file2.read())

    def _test_identity(self, ci):
        first = os.path.join(self.tmp_dir, "first")
        second = os.path.join(self.tmp_dir, "second")

        # write original file
        ci.dump(first)

        # read file and write it back
        ci = ComposeInfo()
        ci.load(first)
        ci.dump(second)

        # check if first and second files are identical
        self.assertSameFiles(first, second)

    def test_create(self):
        ci = ComposeInfo()
        ci.release.name = "Fedora"
        ci.release.short = "F"
        ci.release.version = "22"
        ci.release.type = "ga"

        ci.compose.id = "F-22-20150522.0"
        ci.compose.type = "production"
        ci.compose.date = "20150522"
        ci.compose.respin = 0

        variant = Variant(ci)
        variant.id = "Server"
        variant.uid = "Server"
        variant.name = "Server"
        variant.type = "variant"
        variant.arches = set(["armhfp", "i386", "x86_64"])

        ci.variants.add(variant)

        ci.dump(self.ci_path)
        self._test_identity(ci)
        return ci

    def test_is_ga(self):
        ci = self.test_create()
        self.assertEqual(ci.compose.final, False)
        self.assertEqual(ci.compose.is_ga, False)
        ci.dump(self.ci_path)

        ci.compose.final = True
        self.assertEqual(ci.compose.final, True)
        self.assertEqual(ci.compose.is_ga, False)
        ci.dump(self.ci_path)

        ci.compose.label = "Beta-2.1"
        self.assertEqual(ci.compose.final, True)
        self.assertEqual(ci.compose.is_ga, False)
        ci.dump(self.ci_path)

        ci.compose.label = "RC-2.1"
        self.assertEqual(ci.compose.final, True)
        self.assertEqual(ci.compose.is_ga, True)
        ci.dump(self.ci_path)

        # GA is not a valid label; GA is the last RC that is marked as final
        ci.compose.label = "GA"
        self.assertRaises(ValueError, ci.dump, self.ci_path)

    def test_release_non_numeric_version(self):
        r = Release(None)
        r.name = "Fedora"
        r.short = "f"
        r.version = "Rawhide"
        r.type = "ga"

        r.validate()

    def test_release_empty_version(self):
        r = Release(None)
        r.name = "Fedora"
        r.short = "f"
        r.version = ""
        r.type = "ga"

        self.assertRaises(ValueError, r.validate)

    def test_create_variants_with_dash(self):
        ci = ComposeInfo()
        ci.release.name = "Fedora"
        ci.release.short = "F"
        ci.release.version = "22"
        ci.release.type = "ga"

        ci.compose.id = "F-22-20150522.0"
        ci.compose.type = "production"
        ci.compose.date = "20150522"
        ci.compose.respin = 0

        # 2 Tools variants: one for Server, one for Workstation
        # but parent variants are not part of the compose
        variant = Variant(ci)
        variant.id = "ServerTools"
        variant.uid = "Server-Tools"
        variant.name = "Tools"
        variant.type = "variant"
        variant.arches = set(["x86_64"])
        ci.variants.add(variant)
        ci.variants["Server-Tools"]

        variant = Variant(ci)
        variant.id = "WorkstationTools"
        variant.uid = "Workstation-Tools"
        variant.name = "Tools"
        variant.type = "variant"
        variant.arches = set(["x86_64"])
        ci.variants.add(variant)
        ci.variants["Workstation-Tools"]

        ci.dump(self.ci_path)
        self._test_identity(ci)
        return ci

    def test_create_with_prefixed_uid(self):
        ci = ComposeInfo()
        ci.release.name = "Fedora"
        ci.release.short = "F"
        ci.release.version = "22"
        ci.release.type = "ga"

        ci.compose.id = "F-22-20150522.0"
        ci.compose.type = "production"
        ci.compose.date = "20150522"
        ci.compose.respin = 0

        # 2 Tools variants: one for Server, one for Workstation
        # but parent variants are not part of the compose
        variant = Variant(ci)
        variant.id = "Foo"
        variant.uid = "Foo"
        variant.name = "Foo"
        variant.type = "variant"
        variant.arches = set(["x86_64"])
        ci.variants.add(variant)
        ci.variants["Foo"]

        variant = Variant(ci)
        variant.id = "FooBar"
        variant.uid = "Foo-Bar"
        variant.name = "Foo-Bar"
        variant.type = "variant"
        variant.arches = set(["x86_64"])
        ci.variants.add(variant)
        ci.variants["Foo-Bar"]

        ci.dump(self.ci_path)
        self._test_identity(ci)
        return ci

    def test_get_variants(self):
        ci = ComposeInfo()
        ci.release.name = "Fedora"
        ci.release.short = "F"
        ci.release.version = "25"
        ci.release.type = "ga"

        ci.compose.id = "F-25-20150522.0"
        ci.compose.type = "production"
        ci.compose.date = "20161225"
        ci.compose.respin = 0

        variant = Variant(ci)
        variant.id = "Server"
        variant.uid = "Server"
        variant.name = "Server"
        variant.type = "variant"
        variant.arches = set(["armhfp", "i386", "x86_64"])

        ci.variants.add(variant)
        ci.get_variants()
        self.assertEqual(ci.get_variants(), [variant])
        self.assertEqual(ci.get_variants(arch='x86_64'), [variant])

    def test_multiple_variants(self):
        ci = ComposeInfo()
        ci.release.name = "Fedora"
        ci.release.short = "F"
        ci.release.version = "25"
        ci.release.type = "ga"

        ci.compose.id = "F-25-20150522.0"
        ci.compose.type = "production"
        ci.compose.date = "20161225"
        ci.compose.respin = 0

        varianta = Variant(ci)
        varianta.id = "Server"
        varianta.uid = "Server"
        varianta.name = "Server"
        varianta.type = "variant"
        varianta.arches = set(["armhfp", "i386", "x86_64"])

        variantb = Variant(ci)
        variantb.id = "Client"
        variantb.uid = "Client"
        variantb.name = "Client"
        variantb.type = "variant"
        variantb.arches = set(["armhfp", "i386", "x86_64"])

        ci.variants.add(varianta)
        ci.variants.add(variantb)
        ci.get_variants()
        self.assertEqual(ci.get_variants(), [variantb, varianta])
        self.assertEqual(ci.get_variants(arch='x86_64'), [variantb, varianta])


class TestCreateComposeID(unittest.TestCase):
    def setUpRelease(self, compose_type, release_type, bp_type=None):
        self.ci = ComposeInfo()
        self.ci.release.name = 'Fedora'
        self.ci.release.short = 'F'
        self.ci.release.version = '22'
        self.ci.release.type = release_type
        self.ci.compose.date = '20160622'
        self.ci.compose.respin = 0
        self.ci.compose.type = compose_type

        if bp_type:
            self.ci.release.is_layered = True
            self.ci.base_product.short = 'BASE'
            self.ci.base_product.version = '3'
            self.ci.base_product.type = bp_type


def setup_create_compose_id_case():
    def test_generator(compose_id, *args):
        def test(self):
            self.setUpRelease(*args)
            self.assertEqual(self.ci.create_compose_id(), compose_id)
        return test

    data = [
        # Expected compose id                        compose type   release type  base product type
        ('F-22-20160622.0',                          'production',  'ga'),
        ('F-22-20160622.n.0',                        'nightly',     'ga'),
        ('F-22-20160622.ci.0',                       'ci',          'ga'),
        ('F-22-updates-20160622.0',                  'production',  'updates'),
        ('F-22-updates-20160622.n.0',                'nightly',     'updates'),
        ('F-22-BASE-3-20160622.0',                   'production',  'ga',        'ga'),
        ('F-22-BASE-3-20160622.n.0',                 'nightly',     'ga',        'ga'),
        ('F-22-updates-BASE-3-20160622.0',           'production',  'updates',   'ga'),
        ('F-22-updates-BASE-3-20160622.n.0',         'nightly',     'updates',   'ga'),
        ('F-22-BASE-3-updates-20160622.0',           'production',  'ga',        'updates'),
        ('F-22-BASE-3-updates-20160622.n.0',         'nightly',     'ga',        'updates'),
        ('F-22-updates-BASE-3-updates-20160622.0',   'production',  'updates',   'updates'),
        ('F-22-updates-BASE-3-updates-20160622.n.0', 'nightly',     'updates',   'updates'),
        ('F-22-updates-BASE-3-updates-20160622.d.0', 'development', 'updates',   'updates'),
    ]
    for args in data:
        test_name = 'test_compose_%s_release_%s' % (args[1], args[2])
        if len(args) == 4:
            test_name += '_base_%s' % args[3]
        test = test_generator(*args)
        setattr(TestCreateComposeID, test_name, test)

setup_create_compose_id_case()


class TestGetDateTypeRespin(unittest.TestCase):

    def test_unknown_type(self):
        self.assertRaises(ValueError, get_date_type_respin, 'Foo-1.0-20170217.foo.2')

    def test_unknown_type_matching_prefix(self):
        self.assertRaises(ValueError, get_date_type_respin, 'Foo-1.0-20170217.c.2')

    def test_explicit_production(self):
        self.assertRaises(ValueError, get_date_type_respin, 'Foo-1.0-20170217.production.2')


def setup_get_date_type_case():
    def test_generator(cid, date, type, respin):
        def test(self):
            self.assertEqual(
                get_date_type_respin(cid),
                (date, type, respin)
            )
        return test

    data = {
        'bad_format': ('Hello', None, None, None),
        'production': ('Foo-1.0-20170217.1', '20170217', 'production', 1),
        'nightly': ('Foo-1.0-20170217.n.1', '20170217', 'nightly', 1),
        'ci': ('Foo-1.0-20170217.ci.1', '20170217', 'ci', 1),
        'no_respin': ('Foo-1.0-20170217.ci', '20170217', 'ci', 0),
        'development': ('Foo-1.0-20170217.d.1', '20170217', 'development', 1),
    }
    for name in data:
        test_name = 'test_%s' % name
        test = test_generator(*data[name])
        setattr(TestGetDateTypeRespin, test_name, test)

setup_get_date_type_case()

if __name__ == "__main__":
    unittest.main()
