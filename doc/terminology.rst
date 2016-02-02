===========
Terminology
===========


.. _Release:

Release
=======
(Product) :ref:`Release` is a collection of software with unique identity and life cycle.

**Notes**
  * It is advised to separate updates from minor releases for better content tracking.
  * Release should be immutable - once a release is finished, it's content or definition must never change.
  * When designing metadata or data schemas, :ref:`Releases <Release>` should carry all information even if there is certain duplicity.
    :ref:`Product Versions <Product Version>` and :ref:`Products <Product>` should not carry any data. These are only for grouping and organizing :ref:`Releases <Release>`.

**Examples**
  * Fedora 21 (f-21)
  * Fedora 21 Updates (f-21-updates)
  * Red Hat Enterprise Linux 7.0 (rhel-7.0)
  * Red Hat Enterprise Linux 7.1 (rhel-7.1)
  * Satellite 5.6.0 for Red Hat Enterprise Linux 7 (satellite-5.6.0-rhel7)


.. _Product Version:

Product Version
===============
:ref:`Product Version` is a group of product :ref:`Releases <Release>` with the same name and major version.

**Examples**
  * Fedora 21 (f-21)
  * Red Hat Enterprise Linux 7 (rhel-7)
  * Satellite 5.6 (satellite-5.6)


.. _Product:

Product
=======
:ref:`Product` is a group of :ref:`Product Versions <Product Version>` with the same name.

**Examples**
  * Fedora (f)
  * Red Hat Enterprise Linux (rhel)
  * Satellite (satellite)


.. _Base Product:

Base Product
============
:ref:`Base Product` usually indicates operating system a :ref:`Release` runs on.
In reality it often matches with :ref:`Product Version` of that OS.

**Examples**
  * Fedora 21
  * Red Hat Enteprise Linux 7


.. _Compose:

Compose
=======
:ref:`Compose` is a :ref:`Release` snapshot with an unique ID derived from :ref:`Release` and compose date.

**Notes**
  * :ref:`Compose` should consist of well defined building blocks, ideally described by metadata (.treeinfo, repodata, ...)

**Examples**
  * RHEL-7.0-YYYYMMDD.0
  * Satellite-5.6.0-RHEL-7-YYYYMMDD.0


.. _Variant:

Variant
=======
Both :ref:`Composes <Compose>` and :ref:`Releases <Release>` are divide into :ref:`Variants <Variant>`.
These contain different :ref:`Release` content subsets targeting different users (Server, Workstation).

**Examples**
  * RHEL-7.0-YYYYMMDD.0 / Server
  * RHEL-7.0-YYYYMMDD.0 / Workstation


.. _Tree:

Tree
====
:ref:`Tree` is a :ref:`Variant` for specified architecture.

**Examples**
  * RHEL-7.0-YYYYMMDD.0 / Server / x86_64
  * RHEL-7.0-YYYYMMDD.0 / Server / ppc64
  * RHEL-7.0-YYYYMMDD.0 / Workstation / x86_64


==========
Versioning
==========
Versioning should be as simple as possible.
Recommended schema is dot separated numbers:

* **X** -- major version / product version
* **X.Y** -- minor version / update version / release version
* **X.Y.Z** -- bugfix version / hotfix version


.. note ::
    It is technically possible to use arbitrary string as a version, but this
    is highly discouraged as it does not allow sorting. If you need it, just
    start your version with any non-digit character.


.. _Milestones:

==========
Milestones
==========
Milestones are just labels on a :ref:`Release`.
They shouldn't affect how a :ref:`Release` is versioned (e.g. no :ref:`Release` version change on Beta).

**Milestone Labels**
  * <milestone_name>-<version>.<respin>
  * <milestone_name>-<version> stands for planned milestone
  * <respin> is internal-only numbering

**Milestone Names**
  * DevelPhaseExit -- DEV finished major features, QE performs acceptance testing for entering the Testing phase
  * InternalAlpha -- Internal Alpha, usually tweaking compose for the first public release
  * Alpha -- Public Alpha
  * InternalSnapshot -- Snapshots between Alpha and Beta, usually only for QE purposes
  * Beta -- Public Beta
  * Snapshot -- Snapshots between Beta and RC
  * RC -- Release Candidates
  * Update -- post-GA updates

**Examples**
  * (rhel-7.0) Alpha-1.0
  * (rhel-7.0) Beta-1.0
  * (rhel-7.0) Beta-1.1
