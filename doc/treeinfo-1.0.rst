========================
Treeinfo file format 1.0
========================

Treeinfo files provide details about installable trees in Fedora composes and media.

File Format
===========

Treeinfo is an INI file.
It's recommended to sort sections and keys alphabetically
in order to diff .treeinfo files easily.

::

  [header]
  version = 1.0                         ; metadata version; format: $major<int>.$minor<int>

  [release]
  name = <str>                          ; release name, for example: "Fedora", "Red Hat Enterprise Linux", "Spacewalk"
  short = <str>                         ; release short name, for example: "F", "RHEL", "Spacewalk"
  version = <str>                       ; release version, for example: "21", "7.0", "2.1"
  is_layered = <bool=False>             ; typically False for an operating system, True otherwise

  [base_product]
  name = <str>                          ; base product name, for example: "Fedora", "Red Hat Enterprise Linux"
  short = <str>                         ; base product short name, for example: "F", "RHEL"
  version = <str>                       ; base product *major* version, for example: "21", "7"

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


Examples
========

Fedora 21 Server.x86_64 .treinfo converted to 1.0 format::

  [checksums]
  images/boot.iso = sha256:56af126a50c227d779a200b414f68ea7bcf58e21c8035500cd21ba164f85b9b4
  images/efiboot.img = sha256:de48c8b25f03861c00c355ccf78108159f1f2aa63d0d63f92815146c24f60164
  images/macboot.img = sha256:da76ff5490b4ae7e123f19b8f4b36efd6b7c435073551978d50c5181852a87f5
  images/product.img = sha256:ffce14a7a95be20b36f302cb0698be8c19fda798807d3d63a491d6f7c1b23b5b
  images/pxeboot/initrd.img = sha256:aadebd07c4c0f19304f0df7535a8f4218e5141602f95adec08ad1e22ff1e2d43
  images/pxeboot/upgrade.img = sha256:224d098fb3903583b491692c5e0e1d20ea840d51f4da671ced97d422402bbf1c
  images/pxeboot/vmlinuz = sha256:81c28a439f1d23786057d3b57db66e00b2b1a39b64d54de1a90cf2617e53c986
  repodata/repomd.xml = sha256:3af1609aa27949bf1e02e9204a7d4da7efee470063dadbc3ea0be3ef7f1f4d14

  [general]
  arch = x86_64
  family = Fedora
  name = Fedora 21
  packagedir = Packages
  platforms = x86_64,xen
  repository = .
  timestamp = 1417653911
  variant = Server
  version = 21

  [header]
  version = 1.0

  [images-x86_64]
  boot.iso = images/boot.iso
  initrd = images/pxeboot/initrd.img
  kernel = images/pxeboot/vmlinuz
  upgrade = images/pxeboot/upgrade.img

  [images-xen]
  initrd = images/pxeboot/initrd.img
  kernel = images/pxeboot/vmlinuz
  upgrade = images/pxeboot/upgrade.img

  [release]
  name = Fedora
  short = Fedora
  version = 21

  [stage2]
  mainimage = LiveOS/squashfs.img

  [tree]
  arch = x86_64
  build_timestamp = 1417653911
  platforms = x86_64,xen
  variants = Server

  [variant-Server]
  id = Server
  name = Server
  packages = Packages
  repository = .
  type = variant
  uid = Server


Original Fedora 21 Server.x86_64 .treinfo file (before conversion)::

  [general]
  name = Fedora-Server-21
  family = Fedora-Server
  timestamp = 1417653911.68
  variant = Server
  version = 21
  packagedir = 
  arch = x86_64

  [stage2]
  mainimage = LiveOS/squashfs.img

  [images-x86_64]
  kernel = images/pxeboot/vmlinuz
  initrd = images/pxeboot/initrd.img
  upgrade = images/pxeboot/upgrade.img
  boot.iso = images/boot.iso

  [images-xen]
  kernel = images/pxeboot/vmlinuz
  initrd = images/pxeboot/initrd.img
  upgrade = images/pxeboot/upgrade.img

  [checksums]
  images/efiboot.img = sha256:de48c8b25f03861c00c355ccf78108159f1f2aa63d0d63f92815146c24f60164
  images/macboot.img = sha256:da76ff5490b4ae7e123f19b8f4b36efd6b7c435073551978d50c5181852a87f5
  images/product.img = sha256:ffce14a7a95be20b36f302cb0698be8c19fda798807d3d63a491d6f7c1b23b5b
  images/boot.iso = sha256:56af126a50c227d779a200b414f68ea7bcf58e21c8035500cd21ba164f85b9b4
  images/pxeboot/vmlinuz = sha256:81c28a439f1d23786057d3b57db66e00b2b1a39b64d54de1a90cf2617e53c986
  images/pxeboot/initrd.img = sha256:aadebd07c4c0f19304f0df7535a8f4218e5141602f95adec08ad1e22ff1e2d43
  images/pxeboot/upgrade.img = sha256:224d098fb3903583b491692c5e0e1d20ea840d51f4da671ced97d422402bbf1c
  repodata/repomd.xml = sha256:3af1609aa27949bf1e02e9204a7d4da7efee470063dadbc3ea0be3ef7f1f4d14
