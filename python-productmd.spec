# ** IMPORTANT NOTE **
# This spec is also tracked in productmd upstream git:
# https://github.com/release-engineering/productmd
# Please synchronize changes to it with upstream.

%bcond_without  python3

Name:           python-productmd
Version:        1.25
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

%package -n python2-productmd
Summary:        %summary
Obsoletes:      productmd <= %{version}-%{release}
Provides:       productmd = %{version}-%{release}
BuildRequires:  python2-devel
%if 0%{?rhel} && 0%{?rhel} <= 7
BuildRequires:  python-setuptools
BuildRequires:  python-six
Requires:       python-six
%else
BuildRequires:  python2-setuptools
BuildRequires:  python2-six
Requires:       python2-six
%endif
%{?python_provide:%python_provide python2-productmd}

%description -n python2-productmd %_description

%if 0%{?with_python3}
%package -n python%{python3_pkgversion}-productmd
Summary:        %{summary}
BuildRequires:  python%{python3_pkgversion}-devel
BuildRequires:  python%{python3_pkgversion}-setuptools
BuildRequires:  python%{python3_pkgversion}-six
Requires:       python%{python3_pkgversion}-six

%description -n python%{python3_pkgversion}-productmd %_description
%endif

%prep
%setup -q

%build
%py2_build

%if 0%{?with_python3}
%py3_build
%endif

%install
%py2_install

%if 0%{?with_python3}
%py3_install
%endif

%check
%{__python2} ./setup.py test

%if 0%{?with_python3}
%{__python3} ./setup.py test
%endif

%files -n python2-productmd
%license LICENSE
%doc AUTHORS
%{python_sitelib}/productmd/
%{python_sitelib}/productmd-%{version}-py?.?.egg-info

%if 0%{?with_python3}
%files -n python%{python3_pkgversion}-productmd
%license LICENSE
%doc AUTHORS
%{python3_sitelib}/productmd/
%{python3_sitelib}/productmd-%{version}-py?.?.egg-info
%endif

%changelog
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
