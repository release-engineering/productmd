%global with_python3 1

%if 0%{?fedora} && 0%{?fedora} <= 12
%global with_python3 0
%endif

%if 0%{?rhel} && 0%{?rhel} <= 7
%{!?__python2: %global __python2 /usr/bin/python2}
%{!?python2_sitelib: %global python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%global with_python3 0
%endif

# compatibility with older releases
%{!?__python2: %global __python2 /usr/bin/python2}
%{!?python2_sitelib: %global python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python2_sitearch: %global python2_sitearch %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%{!?py2_build: %global py2_build %{expand: CFLAGS="%{optflags}" %{__python2} setup.py %{?py_setup_args} build --executable="%{__python2} -s"}}
%{!?py2_install: %global py2_install %{expand: CFLAGS="%{optflags}" %{__python2} setup.py %{?py_setup_args} install -O1 --skip-build --root %{buildroot}}}

Name:           python-productmd
Version:        1.3
Release:        1%{?dist}
Summary:        Library providing parsers for metadata related to OS installation

Group:          Development/Tools
License:        LGPLv2+
URL:            https://github.com/release-engineering/productmd
Source0:        https://files.pythonhosted.org/packages/source/p/%{name}/%{name}-%{version}.tar.gz

Obsoletes:      productmd <= %{version}-%{release}
Provides:       productmd = %{version}-%{release}
Provides:       python2-productmd = %{version}-%{release}

Requires:       python-six

BuildRequires:  python2-devel
BuildRequires:  python-setuptools
BuildRequires:  python-six

%if  0%{?with_python3}
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-six
%endif

BuildArch:      noarch

%description
Python library providing parsers for metadata related to composes
and installation media.

%if 0%{?with_python3}
%package -n python3-productmd
Summary:       Library providing parsers for metadata related to OS installation
Group:         Development/Tools
Requires:      python3-six

%description -n python3-productmd
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
%{!?_licensedir:%global license %doc}

%files
%license LICENSE
%doc AUTHORS
%{python_sitelib}/productmd/
%{python_sitelib}/productmd-%{version}-py?.?.egg-info


%if 0%{?with_python3}
%files -n python3-productmd
%license LICENSE
%doc AUTHORS
%{python3_sitelib}/productmd/
%{python3_sitelib}/productmd-%{version}-py?.?.egg-info
%endif

%changelog
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
