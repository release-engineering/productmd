# ** IMPORTANT NOTE **
# This spec is also tracked in productmd upstream git:
# https://github.com/release-engineering/productmd
# Please synchronize changes to it with upstream.

%bcond_without  python3

Name:           python-productmd
Version:        1.49
Release:        1%{?dist}
Summary:        Library providing parsers for metadata related to OS installation

License:        LGPLv2+
URL:            https://github.com/release-engineering/productmd
Source0:        https://files.pythonhosted.org/packages/source/p/%{name}/%{name}-%{version}.tar.gz

BuildArch:      noarch

%global _description\
Python library providing parsers for metadata related to composes\
and installation media.

%description %_description

%package -n python%{python3_pkgversion}-productmd
Summary:        %{summary}
BuildRequires:  python%{python3_pkgversion}-devel
BuildRequires:  python%{python3_pkgversion}-setuptools

%description -n python%{python3_pkgversion}-productmd %_description

%prep
%setup -q

%build
%py3_build

%install
%py3_install

%check
%{__python3} ./setup.py test

%files -n python%{python3_pkgversion}-productmd
%license LICENSE
%doc AUTHORS
%{python3_sitelib}/productmd/
%{python3_sitelib}/productmd-%{version}-py?.?.egg-info

%changelog
* Mon Nov 24 2025 Lubomír Sedlář <lsedlar@redhat.com> 1.49-1
- Add Accept header to all HTTP requests (lsedlar@redhat.com)
- Set User-Agent header for all HTTP requests (lsedlar@redhat.com)
- Add cache over checking file existence (lsedlar@redhat.com)
- Make HEAD request for checking file existence (lsedlar@redhat.com)
- Remove urllib compatibility with Python 2.7 (lsedlar@redhat.com)

* Tue Jul 08 2025 Lubomír Sedlář <lsedlar@redhat.com> 1.48-1
- Add missing import of urllib.request (lsedlar@redhat.com)

* Mon Jul 07 2025 Lubomír Sedlář <lsedlar@redhat.com> 1.47-1
- Add missing import of urllib.error (lsedlar@redhat.com)

* Fri Jul 04 2025 Lubomír Sedlář <lsedlar@redhat.com> 1.46-1
- Add 'wsl' format for wsl2 images (awilliam@redhat.com)
- Drop Python 2 support (dalley@redhat.com)

* Mon Apr 14 2025 Lubomír Sedlář <lsedlar@redhat.com> 1.45-1
- Rename wsl to wsl2 (lsedlar@redhat.com)

* Fri Apr 11 2025 Lubomír Sedlář <lsedlar@redhat.com> 1.44-1
- Add wsl image type (lsedlar@redhat.com)
- add OS support UOS and Kylin (yurii.huang@dbappsecurity.com.cn)
- Add Python 3.13 to CI (lsedlar@redhat.com)

* Mon Dec 09 2024 Lubomír Sedlář <lsedlar@redhat.com> 1.43-1
- images: add more container types, move fex for alphabetical order
  (awilliam@redhat.com)

* Wed Nov 20 2024 Lubomír Sedlář <lsedlar@redhat.com> 1.42-1
- images: add type and formats for erofs and squashfs to back FEX
  (awilliam@redhat.com)

* Mon Nov 04 2024 Lubomír Sedlář <lsedlar@redhat.com> 1.41-1
- common: Update RPM_ARCHES to match dnf (abologna@redhat.com)

* Thu Aug 29 2024 Lubomír Sedlář <lsedlar@redhat.com> 1.40-1
- Remove 'iso' image type again (awilliam@redhat.com)

* Wed Aug 28 2024 Lubomír Sedlář <lsedlar@redhat.com> 1.39-1
- Add mappings for appx and iso types for kiwi image builds
  (ngompa@velocitylimitless.com)

* Thu Dec 07 2023 Lubomír Sedlář <lsedlar@redhat.com> 1.38-1
- Add ociarchive image type (lsedlar@redhat.com)
- Run bandit in github action (lsedlar@redhat.com)
- Create a github action to run tests (lsedlar@redhat.com)
- Update list of python versions in tox.ini (lsedlar@redhat.com)
- Set up security scanning with bandit (lsedlar@redhat.com)

* Fri Sep 22 2023 Lubomír Sedlář <lsedlar@redhat.com> 1.37-1
- images: add `dvd-ostree-osbuild` image type (cmdr@supakeen.com)
- images: add `live-osbuild` image type (cmdr@supakeen.com)

* Thu Jul 27 2023 Lubomír Sedlář <lsedlar@redhat.com> 1.36-1
- Compose: test existence of compose/metadata/composeinfo.json
  (kdreyer@ibm.com)
- Fix tests to pass on ancient version of python (mhaluza@redhat.com)

* Tue Feb 28 2023 Lubomír Sedlář <lsedlar@redhat.com> 1.35-1
- Fix support for ftp protocol when fetching metadata (zveleba@redhat.com)

* Tue Feb 14 2023 Lubomír Sedlář <lsedlar@redhat.com> 1.34-1
- Add vhd-compressed image type (lsedlar@redhat.com)
- Add support for euleros (zhuofeng2@huawei.com)

* Mon May 24 2021 Lubomír Sedlář <lsedlar@redhat.com> 1.33-1
- Add ability to set a main variant while dumping TreeInfo:
  (soksanichenko@cloudlinux.com)

* Fri Apr 16 2021 Lubomír Sedlář <lsedlar@redhat.com> 1.32-1
- Update macros in spec file (lsedlar@redhat.com)
- fix release short name validated failed when running on other linux
  distributions (t.feng94@foxmail.com)

* Mon Feb 08 2021 Lubomír Sedlář <lsedlar@redhat.com> 1.31-1
- Add py39 to tox (lsedlar@redhat.com)
- Explicitly list six as a test dependency (lsedlar@redhat.com)
- Handle build_timestamp in the float format (ttereshc@redhat.com)

* Thu Nov 26 2020 Lubomír Sedlář <lsedlar@redhat.com> 1.30-1
- Support ftp protocol when fetching metadata. (pholica@redhat.com)

* Tue Nov 10 2020 Lubomír Sedlář <lsedlar@redhat.com> 1.29-1
- Include non-ISO images in composeinfo (hlin@redhat.com)

* Fri Sep 25 2020 Lubomír Sedlář <lsedlar@redhat.com> 1.28-1
- Add 'development' compose type for non-production version of compose.
  (jkaluza@redhat.com)
- Use tar.gz for source distribution (lsedlar@redhat.com)

* Tue Aug 18 2020 Haibo Lin <hlin@redhat.com> 1.27-1
- Fix VariantBase._validate_variants() (hlin@redhat.com)
- Fix validation for optional variant (hlin@redhat.com)

* Thu Apr 09 2020 Lubomír Sedlář <lsedlar@redhat.com> 1.26-1
- Fix validation for top-level Variant UIDs with dashes (hlin@redhat.com)

* Mon Mar 23 2020 Lubomír Sedlář <lsedlar@redhat.com> 1.25-1
- Allow passing arguments to pytest via tox (lsedlar@redhat.com)
- Relax validations enough to parse OpenSUSE treeinfo (lsedlar@redhat.com)

* Fri Feb 07 2020 Lubomír Sedlář <lsedlar@redhat.com> 1.24-1
- Fix dumping extra_files metadata when CWD is deleted (lsedlar@redhat.com)
- Make tests pass on Python 2.6 (lsedlar@redhat.com)

* Thu Oct 31 2019 Lubomír Sedlář <lsedlar@redhat.com> 1.23-1
- Add class for representing extra files in the compose (lsedlar@redhat.com)
- Add tests for multiple variants in one .treeinfo (riehecky@fnal.gov)

* Wed Sep 04 2019 Lubomír Sedlář <lsedlar@redhat.com> 1.22-1
- Fix parsing composeinfo with almost conflicting UIDs (lsedlar@redhat.com)
- Improve error message for invalid metadata (lsedlar@redhat.com)
- Fix image format for vpc (lsedlar@redhat.com)
- Set up test infrastructure (lsedlar@redhat.com)
- Add missing parts to the TreeInfo documentation (jkonecny@redhat.com)
- Add a comment explaining the 'tar-gz' type (awilliam@redhat.com)

* Mon Mar 11 2019 Lubomír Sedlář <lsedlar@redhat.com> 1.21-1
- Correct a typo in IMAGE_TYPE_FORMAT_MAPPING (awilliam@redhat.com)

* Tue Mar 05 2019 Lubomír Sedlář <lsedlar@redhat.com> 1.20-1
- Keep image types synced with formats (lsedlar@redhat.com)

* Thu Jan 24 2019 Lubomír Sedlář <lsedlar@redhat.com> 1.19-1
- Fix extracting minor version from long string (lsedlar@redhat.com)
- Add new release types for BaseProduct (onosek@redhat.com)
- add __version__ attribute (kdreyer@redhat.com)
- images: add doc example for using the Images class (kdreyer@redhat.com)

* Fri Nov 23 2018 Lubomír Sedlář <lsedlar@redhat.com> 1.18-1
- get_major_version should always return first component (lsedlar@redhat.com)
- Add SecurityFix label (lsedlar@redhat.com)

* Fri Oct 05 2018 Lubomír Sedlář <lsedlar@redhat.com> 1.17-1
- Add additional_variants attribute to unified images (lsedlar@redhat.com)
- Do not use custom repr for objects with no compose (jkonecny@redhat.com)
- README: link to readthedocs (kdreyer@redhat.com)

* Fri Jun 22 2018 Lubomír Sedlář <lsedlar@redhat.com> 1.16-1
- Allow modules without metadata (lsedlar@redhat.com)

* Wed Jun 20 2018 Lubomír Sedlář <lsedlar@redhat.com> 1.15-1
- Add missing _modules attribute to Compose (lsedlar@redhat.com)
- composeinfo: add docs for Compose class (kdreyer@redhat.com)
- rpms: add doc example for using the Rpms class (kdreyer@redhat.com)
- common: document parse_nvra() return value elements (kdreyer@redhat.com)
- common: explain filename handling for parse_nvra() (kdreyer@redhat.com)

* Fri May 11 2018 Lubomír Sedlář <lsedlar@redhat.com> 1.14-1
- Add rhevm-ova as valid type (lsedlar@redhat.com)

* Thu May 10 2018 Lubomír Sedlář <lsedlar@redhat.com> 1.13-1
- Add vsphere-ova as valid image type (lsedlar@redhat.com)

* Mon May 07 2018 Lubomír Sedlář <lsedlar@redhat.com> 1.12-1
- Add vpc type and vhd format for images (lsedlar@redhat.com)

* Thu Mar 29 2018 Lubomír Sedlář <lsedlar@redhat.com> 1.11-1
- New class for processing modules (onosek@redhat.com)
- packaging: fixes (ignatenko@redhat.com)

* Wed Jan 17 2018 Lubomír Sedlář <lsedlar@redhat.com> 1.10-1
- Drop Fedora 25 build (lsedlar@redhat.com)
- Drop RHEL compatibility from spec (lsedlar@redhat.com)
- Use more relaxed release type checks (lholecek@redhat.com)
- Fix parse release id with dash in type (lsedlar@redhat.com)
- Add tests for parse_release_id() (lholecek@redhat.com)
- Update dependencies to include Python version (#97)

* Tue Oct 24 2017 Lubomír Sedlář <lsedlar@redhat.com> 1.9-1
- add updates-testing as a valid compose type (#96)
  (dgilmore@fedoraproject.org)
- Update tito configuration (lsedlar@redhat.com)

* Wed Oct 11 2017 Lubomír Sedlář <lsedlar@redhat.com> 1.8-1
- Report better error on parsing invalid JSON (#95) (lubomir.sedlar@gmail.com)
- Python 2 binary package renamed to python2-productmd (zbyszek@in.waw.pl)
- Sync spec file with Fedora (#94) (lubomir.sedlar@gmail.com)

* Sat Aug 19 2017 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 1.7-3
- Python 2 binary package renamed to python2-productmd
  See https://fedoraproject.org/wiki/FinalizingFedoraSwitchtoPython3

* Thu Jul 27 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.7-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Wed Apr 19 2017 Lubomír Sedlář <lsedlar@redhat.com> 1.7-1
- common: omit context kwarg to urlopen on old Python (lsedlar@redhat.com)

* Thu Apr 06 2017 Lubomír Sedlář <lsedlar@redhat.com> 1.6-1
- Add a new image type dvd-debuginfo (lsedlar@redhat.com)
- Add Tito release for F26 (lsedlar@redhat.com)

* Tue Apr 04 2017 Lubomír Sedlář <lsedlar@redhat.com> 1.5-1
- Add 'unified' to unique image attributes (lsedlar@redhat.com)
- Add EA - Early Access label (lkocman@redhat.com)
- Correctly parse type from ci compose (lsedlar@redhat.com)
- Simplify tests for creating compose id (lsedlar@redhat.com)
- Sync spec file with Fedora (enable Py3 for EPEL) (#79) (awilliam@redhat.com)
- Support 'unique image identifier' concept, enforce on 1.1+
  (awilliam@redhat.com)

* Wed Feb 15 2017 Adam Williamson <awilliam@redhat.com>
- Restore compatibility cruft for pure-RHEL builds

* Sat Feb 11 2017 Fedora Release Engineering <releng@fedoraproject.org> - 1.4-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Fri Feb 10 2017 Adam Williamson <awilliam@redhat.com> - 1.4-2
- Enable Python 3 build for EL 6+

* Tue Jan 10 2017 Lubomír Sedlář <lsedlar@redhat.com> 1.4-1
- Fix loading variants from legacy composeinfo. (dmach@redhat.com)
- Fix sorting composes (lsedlar@redhat.com)
- Compose: scan all subdirs under compose_path for metadata.
  (dmach@redhat.com)
- Add Python 3.6 on Travis (lsedlar@redhat.com)
- tests: add tests for ComposeInfo.get_variants() (kdreyer@redhat.com)
- tests: composeinfo variant arches are sets (kdreyer@redhat.com)
- composeinfo: py3 support for sort in get_variants() (kdreyer@redhat.com)
- composeinfo: py3 support for iter in get_variants() (kdreyer@redhat.com)
- composeinfo: check variant arches as a set (kdreyer@redhat.com)
- composeinfo: fix arch kwarg handling in get_arches() (kdreyer@redhat.com)
- Configure bztar with setup.cfg (lsedlar@redhat.com)
- Remove requirements.txt (lsedlar@redhat.com)
- Include requirements.txt in tarball (lsedlar@redhat.com)
- Move %%license definition just before %%files (lsedlar@redhat.com)
- Remove builder.test from releasers.conf (lsedlar@redhat.com)
- Install deps with setup.py on Travis (lsedlar@redhat.com)

* Wed Nov 23 2016 Lubomír Sedlář <lsedlar@redhat.com> 1.3-1
- new package built with tito

* Tue Jul 19 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.2-2
- https://fedoraproject.org/wiki/Changes/Automatic_Provides_for_Python_RPM_Packages

* Thu Jun 02 2016 Lubomír Sedlář <lsedlar@redhat.com> - 1.2-1
- New upstream release
- Update source url to point to PyPI
- Allow numbers in variant IDs. (dmach)
- Add support for top-level variant UIDs with dashes. (dmach)
- Change JSON separators to unify behavior on py2 and py3. (dmach)
- Move src images under binary arches. (dmach)
- Silence flake8 by moving module imports to top. (dmach)
- Forbid 'src' arch in images.json and rpms.json. (dmach)
- Include tests/images data in MANIFEST.in. (dmach)
- Add docstring to Header class (lsedlar)

* Mon Apr 25 2016 Lubomír Sedlář <lsedlar@redhat.com> - 1.1-1
- new upstream release
- use .tar.gz tarball from github
- removed patches as they are merged upstream

* Fri Mar 11 2016 Dennis Gilmore <dennsi@ausil.us> - 1.0-13
- add patch for supporting subvariant

* Thu Feb 18 2016 Dennis Gilmore <dennis@ausil.us> - 1.0-12
- add a patch to make rawhide as a version consistently an option

* Thu Feb 18 2016 Dennis Gilmore <dennis@ausil.us> - 1.0-11
- update from git to allow us to use rawhide as the version

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 1.0-10
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Tue Jan 26 2016 Dennis Gilmore <dennis@ausil.us> - 1.0-10
- provide python2-productmd
- remove defattr

* Fri Dec 11 2015 Daniel Mach <dmach@redhat.com> - 1.0-9
- Use v1.0 tarball from github
- Fix spec for el6 (license macro)
- Add dependency on python(3)-six

* Wed Dec 09 2015 Dennis Gilmore <dennis@ausil.us> - 1.0-8.git3b72969
- enable building only on python 2 on epel

* Tue Nov 10 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0-7.git3b72969
- Rebuilt for https://fedoraproject.org/wiki/Changes/python3.5

* Tue Nov 03 2015 Dennis Gilmore <dennis@ausil.us> - 1.0-6.git3b72969
- update git snapshot
- rebuild for python-3.5

* Thu Jun 18 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0-5.gitec8c627
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Sun Jun 07 2015 Dennis Gilmore <dennis@ausil.us> - 1.0-4.gitec8c627
- update git snapshot to latest git head with fixes for pungi

* Fri Mar 13 2015 Dennis Gilmore <dennis@ausil.us> - 1.0-3.git57efab
- rename to python-productmd

* Wed Mar 11 2015 Dennis Gilmore <dennis@ausil.us> - 1.0-2.git57efab
- update git tarball so we can run tests at build time

* Tue Mar 10 2015 Dennis Gilmore <dennis@ausil.us> - 1.0-1
- Initial packaging
