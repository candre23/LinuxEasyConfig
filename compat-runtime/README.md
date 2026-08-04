# Linux Easy Config Qt compatibility runtime

This directory builds a reusable binary package containing only the Qt for
Python runtime needed by LEC:

- PySide6 Essentials
- Shiboken6

It installs under:

    /opt/linuxeasyconfig/qt-runtime

The main LEC package remains small and uses this runtime automatically when it
is installed. On a distribution that provides native PySide6 packages, this
compatibility package is unnecessary.

## Build

Run from outside the LEC development virtual environment:

    cd ~/Projects/lec
    python3 compat-runtime/build_compat_runtime.py

The resulting package is written one directory above the project by default:

    ~/Projects/linuxeasyconfig-qt-runtime_6.11.1-1_amd64.deb

The build requires:

    sudo apt install python3-pip dpkg-dev

## Install on Ubuntu 24.04 LTS or Linux Mint 22.3 (x86-64)

Install the runtime first, then LEC:

    sudo apt install ./linuxeasyconfig-qt-runtime_6.11.1-1_amd64.deb
    sudo apt install ./linuxeasyconfig_1.0.0_all.deb

Future LEC updates reuse the installed compatibility runtime.

## Scope

This package currently targets:

- x86-64 (`amd64`)
- Python 3.12 through 3.14
- glibc 2.34 or newer

A separate build is required for ARM64.
