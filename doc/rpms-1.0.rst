====================
RPMs file format 1.0
====================

rpms.json files provide details about RPMs included in composes.


File Format
===========

Compose RPMs metadata is stored as a JSON serialized dictionary.
It's recommended to sort keys alphabetically and use 4 spaces for indentation
in order to read and diff rpms.json files easily.

::

    {
        "header": {
            "version": "1.0"                            # metadata version; format: $major<int>.$minor<int>
        },
        "payload": {
            "compose": {                                # see composeinfo for details
                "date": <str>,
                "id": <str>,
                "respin": <int>,
                "type": <str>
            },
            "rpms": {
                variant_uid<str>: {                     # compose variant UID
                    arch<str>: {                        # compose variant arch
                        srpm_nevra<str>: {              # %name-%epoch:%version-%release-%arch of source RPM (koji build with epoch included)
                            rpm_nevra<str>: {           # %name-%epoch:%version-%release-%arch of RPM file
                                "path": <str>,          # relative path to RPM file
                                "sigkey": <str|null>,   # sigkey ID: hex string 8 characters long, lower case; null for unsigned RPMs
                                "category": <str>       # binary, debug, source
                            }
                        }
                    }
                }
            }
        }
    }


Examples
========

Bash in Fedora 21::

    {
        "header": {
            "version": "1.0"
        },
        "payload": {
            "compose": {
                "date": "20141203",
                "id": "Fedora-21-20141203.0",
                "respin": 0,
                "type": "production"
            },
            "rpms": {
                "Server": {
                    "armhfp": {
                        "bash-0:4.3.30-2.fc21.src": {
                            "bash-0:4.3.30-2.fc21.armv7hl": {
                                "path": "Server/armhfp/os/Packages/b/bash-4.3.30-2.fc21.armv7hl.rpm",
                                "sigkey": "95a43f54",
                                "category": "binary"
                            },
                            "bash-0:4.3.30-2.fc21.src": {
                                "path": "Server/source/SRPMS/b/bash-4.3.30-2.fc21.src.rpm",
                                "sigkey": "95a43f54",
                                "category": "binary"
                            }
                        }
                    },
                    "i386": {
                        "bash-0:4.3.30-2.fc21.src": {
                            "bash-0:4.3.30-2.fc21.i686": {
                                "path": "Server/i386/os/Packages/b/bash-4.3.30-2.fc21.i686.rpm",
                                "sigkey": "95a43f54",
                                "category": "binary"
                            },
                            "bash-0:4.3.30-2.fc21.src": {
                                "path": "Server/source/SRPMS/b/bash-4.3.30-2.fc21.src.rpm",
                                "sigkey": "95a43f54",
                                "category": "binary"
                            }
                        }
                    },
                    "x86_64": {
                        "bash-0:4.3.30-2.fc21.src": {
                            "bash-0:4.3.30-2.fc21.x86_64": {
                                "path": "Server/x86_64/os/Packages/b/bash-4.3.30-2.fc21.x86_64.rpm",
                                "sigkey": "95a43f54",
                                "category": "binary"
                            },
                            "bash-0:4.3.30-2.fc21.src": {
                                "path": "Server/source/SRPMS/b/bash-4.3.30-2.fc21.src.rpm",
                                "sigkey": "95a43f54",
                                "category": "binary"
                            }
                        }
                    }
                },
                "Workstation": {
                    "armhfp": {
                        "bash-0:4.3.30-2.fc21.src": {
                            "bash-0:4.3.30-2.fc21.armv7hl": {
                                "path": "Workstation/armhfp/os/Packages/b/bash-4.3.30-2.fc21.armv7hl.rpm",
                                "sigkey": "95a43f54",
                                "category": "binary"
                            },
                            "bash-0:4.3.30-2.fc21.src": {
                                "path": "Workstation/source/SRPMS/b/bash-4.3.30-2.fc21.src.rpm",
                                "sigkey": "95a43f54",
                                "category": "binary"
                            }
                        }
                    },
                    "i386": {
                        "bash-0:4.3.30-2.fc21.src": {
                            "bash-0:4.3.30-2.fc21.i686": {
                                "path": "Workstation/i386/os/Packages/b/bash-4.3.30-2.fc21.i686.rpm",
                                "sigkey": "95a43f54",
                                "category": "binary"
                            },
                            "bash-0:4.3.30-2.fc21.src": {
                                "path": "Workstation/source/SRPMS/b/bash-4.3.30-2.fc21.src.rpm",
                                "sigkey": "95a43f54",
                                "category": "binary"
                            }
                        }
                    },
                    "x86_64": {
                        "bash-0:4.3.30-2.fc21.src": {
                            "bash-0:4.3.30-2.fc21.x86_64": {
                                "path": "Workstation/x86_64/os/Packages/b/bash-4.3.30-2.fc21.x86_64.rpm",
                                "sigkey": "95a43f54",
                                "category": "binary"
                            },
                            "bash-0:4.3.30-2.fc21.src": {
                                "path": "Workstation/source/SRPMS/b/bash-4.3.30-2.fc21.src.rpm",
                                "sigkey": "95a43f54",
                                "category": "binary"
                            }
                        }
                    }
                }
            }
        }
    }
