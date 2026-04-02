========================
Treeinfo file format 1.2
========================

Treeinfo files provide details about installable trees in Fedora composes and media.


Changes from 1.1
=================

The treeinfo file format is unchanged from 1.1.
The version was bumped to 1.2 due to changes in other metadata files
(``images.json`` no longer allows ``src`` as a standalone architecture;
source images are stored under binary architectures instead).


File Format
===========

Treeinfo is an INI file.
It's recommended to sort sections and keys alphabetically
in order to diff .treeinfo files easily.

::

  [header]
  type = <str>                          ; metadata type; "productmd.treeinfo" required; [new in 1.1]
  version = 1.2                         ; metadata version; format: $major<int>.$minor<int>

  [release]
  name = <str>                          ; release name, for example: "Fedora", "Red Hat Enterprise Linux", "Spacewalk"
  short = <str>                         ; release short name, for example: "F", "RHEL", "Spacewalk"
  version = <str>                       ; release version, for example: "21", "7.0", "2.1"
  type = <str>                          ; release type, for example: "ga", "updates", "eus"; [new in 1.1]
  is_layered = <bool=False>             ; typically False for an operating system, True otherwise

  [base_product]
  name = <str>                          ; base product name, for example: "Fedora", "Red Hat Enterprise Linux"
  short = <str>                         ; base product short name, for example: "F", "RHEL"
  version = <str>                       ; base product *major* version, for example: "21", "7"
  type = <str>                          ; base product release type, for example: "ga", "eus"; [new in 1.1]

  [tree]
  arch = <str>                          ; tree architecture, for example x86_64
  build_timestamp = <int|float>         ; tree build time timestamp; format: unix time
  platforms = <str>[, <str> ...]        ; supported platforms; for example x86_64,xen
  variants = <str>[, <str> ...]         ; UIDs of available variants, for example "Server,Workstation"

  [checksums]
  ; checksums of selected files in a tree:
  ; * all repodata/repomd.xml
  ; * all images captured in [images-*] and [stage2] sections
  $path = $checksum_type<str>:checksum_value<str>

  [images-$platform<str>]
  ; images compatible with particular $platform
  $file_name = $relative_path<str>

  [stage2]
  ; optional section, available only on bootable media with Anaconda installer
  instimage = <str>                     ; relative path to Anaconda instimage (obsolete)
  mainimage = <str>                     ; relative path to Anaconda stage2 image

  [media]
  ; optional section, available only on media
  discnum = <int>                       ; disc number
  totaldiscs = <int>                    ; number of discs in media set

  [variant-$variant_uid]
  id = <str>                            ; variant ID
  uid = <str>                           ; variant UID ($parent_UID.$ID)
  name = <str>                          ; variant name
  type = <str>                          ; variant, optional
  variants = <str>[,<str>...]           ; UIDs of child variants
  addons = <str>[,<str>...]             ; UIDs of child addons

  ; variant paths
  ; all paths are relative to .treeinfo location
  packages = <str>                      ; directory with binary RPMs
  repository = <str>                    ; YUM repository with binary RPMs
  source_packages = <str>               ; directory with source RPMs
  source_repository = <str>             ; YUM repository with source RPMs
  debug_packages = <str>                ; directory with debug RPMs
  debug_repository = <str>              ; YUM repository with debug RPMs
  identity = <str>                      ; path to a pem file that identifies a product

  [addon-$addon_uid]
  id = <str>                            ; addon ID
  uid = <str>                           ; addon UID ($parent_UID.$ID)
  name = <str>                          ; addon name
  type = addon

  ; addon paths
  ; see variant paths

  [general]
  ; WARNING.0 = This section provides compatibility with pre-productmd treeinfos.
  ; WARNING.1 = Read productmd documentation for details about new format.
  family = <str>                        ; equal to [release]/name
  version = <str>                       ; equal to [release]/version
  name = <str>                          ; equal to "$family $version"
  arch = <str>                          ; equal to [tree]/arch
  platforms = <str>[,<str>...]          ; equal to [tree]/platforms
  packagedir = <str>                    ; equal to [variant-*]/packages
  repository = <str>                    ; equal to [variant-*]/repository
  timestamp = <int>                     ; equal to [tree]/build_timestamp
  variant = <str>                       ; variant UID of first variant (sorted alphabetically)
