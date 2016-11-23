Releasing with TITO
===================
Tito is a tool for managing RPM based projects using git for their source code repository.

Tito documentation: https://github.com/dgoodwin/tito


Initial Setup
-------------
### Initialize .tito directory:

    $ tito init

### Setup .tito/releasers.conf
Create sections for all releasers and branches you want to build for,
for example:

    [fedora-rawhide]
    releaser = tito.release.FedoraGitReleaser
    branches = master

### Create spec file in the project's root dir.
Make sure the spec is commited to git to make next steps work.


Test Builds
-----------
### Run local test build

    $ tito build --rpm --offline --test

For initial rpmbuild / spec sanity testing
you can append --rpmbuild-options='--nodeps'
to avoid installing unnecessary deps on your system.


Production Builds
-----------------
### Run a test build first

### Tag build

    $ tito tag

### Release
This creates commits in dist-git and starts builds in koji.

    $ tito release <target> [target] ...

or

    $ tito release --all
