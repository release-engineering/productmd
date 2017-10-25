# ** IMPORTANT NOTE **
# This spec is also tracked in productmd upstream git:
# https://github.com/release-engineering/productmd
# Please synchronize changes to it with upstream, and be aware that
# the spec is used for builds on pure RHEL (i.e. without EPEL packages
# or macros).

# Enable Python 3 builds for Fedora + EPEL >5
# NOTE: do **NOT** change 'epel' to 'rhel' here, as this spec is also
# used to do RHEL builds without EPEL
%if 0%{?fedora} || 0%{?epel} > 5
# If the definition isn't available for python3_pkgversion, define it
%{?!python3_pkgversion:%global python3_pkgversion 3}
%bcond_without  python3
%else
%bcond_with     python3
%endif

# Compatibility with RHEL. These macros have been added to EPEL but
# not yet to RHEL proper.
# https://bugzilla.redhat.com/show_bug.cgi?id=1307190
%{!?__python2: %global __python2 /usr/bin/python2}
%{!?python2_sitelib: %global python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python2_sitearch: %global python2_sitearch %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%{!?py2_build: %global py2_build %{expand: CFLAGS="%{optflags}" %{__python2} setup.py %{?py_setup_args} build --executable="%{__python2} -s"}}
%{!?py2_install: %global py2_install %{expand: CFLAGS="%{optflags}" %{__python2} setup.py %{?py_setup_args} install -O1 --skip-build --root %{buildroot}}}

Name:           python-productmd
Version:        1.9
Release:        1%{?dist}
Summary:        Library providing parsers for metadata related to OS installation

Group:          Development/Tools
License:        LGPLv2+
URL:            https://github.com/release-engineering/productmd
Source0:        https://files.pythonhosted.org/packages/source/p/%{name}/%{name}-%{version}.tar.gz

BuildRequires:  python2-devel
%if 0%{?fedora}
BuildRequires:  python2-setuptools
BuildRequires:  python2-six
%else
BuildRequires:  python-setuptools
BuildRequires:  python-six
%endif

%if 0%{?with_python3}
BuildRequires:  python%{python3_pkgversion}-devel
BuildRequires:  python%{python3_pkgversion}-setuptools
BuildRequires:  python%{python3_pkgversion}-six
%endif

BuildArch:      noarch

%global _description\
Python library providing parsers for metadata related to composes\
and installation media.

%description %_description

%package -n python2-productmd
Summary: %summary
Obsoletes:      productmd <= %{version}-%{release}
Provides:       productmd = %{version}-%{release}
%if 0%{?fedora}
Requires:       python2-six
%else
Requires:       python-six
%endif
%{?python_provide:%python_provide python2-productmd}

%description -n python2-productmd %_description

%if 0%{?with_python3}
%package -n python%{python3_pkgversion}-productmd
Summary:       Library providing parsers for metadata related to OS installation
Group:         Development/Tools
Requires:      python%{python3_pkgversion}-six

%description -n python%{python3_pkgversion}-productmd
Python library providing parsers for metadata related to composes
and installation media.
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

# this must go after all 'License:' tags
# Implemented in EPEL, but not in RHEL
%{!?_licensedir:%global license %doc}

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
