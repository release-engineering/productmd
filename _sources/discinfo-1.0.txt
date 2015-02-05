========================
Discinfo file format 1.0
========================

.discinfo files can be found on Fedora installation media and
provide media information to Anaconda installer.


File Format
===========
.discinfo is a plain-text file containing following fields, one value per line:

::

    timestamp: float
    release: str
    architecture: str
    disc_numbers: ALL or comma separated numbers


Examples
========

Fedora 21 Server.x86_64, disc_numbers: ALL::

    1417653453.026288
    Fedora Server 21
    x86_64
    ALL


Fedora 21 Server.x86_64, disc_numbers: [1, 2, 3]::

    1417653453.026288
    Fedora Server 21
    x86_64
    1,2,3
