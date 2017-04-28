#!/bin/bash

# This script tests the packaging of compdb on Ubuntu Trusty.
# It has been made to run on Travis CI and locally on Ubuntu 14.04,
# or locally inside docker thanks to docker/ubuntu-trusty.sh.
# The dependencies can be found in docker/ubuntu-trusty/Dockerfile.

if [[ ! -f compdb/__init__.py ]]; then
    1>&2 echo "error: this script expects to run in compdb root directory!"
    exit 1
fi

set -o errexit
set -o xtrace

# First generate release files to ~/dist
virtualenv .venv
source .venv/bin/activate
pip install -U "setuptools>=18"
pip install wheel
python setup.py sdist bdist_wheel
deactivate
mv dist ~/dist
rm -r .venv

# Install from source
mkdir ~/userbase
PYTHONUSERBASE=~/userbase python setup.py install --user
PYTHONUSERBASE=~/userbase PATH="$HOME/userbase/bin:$PATH" compdb version
rm -r ~/userbase

# Install from source with pip
mkdir ~/userbase
PYTHONUSERBASE=~/userbase pip install --user .
PYTHONUSERBASE=~/userbase PATH="$HOME/userbase/bin:$PATH" compdb version
rm -r ~/userbase

# Install from source in virtualenv
# On Ubuntu 14.04, system wide setuptools version is 3.3,
# but in virtualenv it is 2.2, which is unsufficient.
virtualenv .venv
source .venv/bin/activate
pip install -U "setuptools>=3.3"
python setup.py install
compdb version
deactivate
rm -r .venv

# Wheel
mkdir ~/userbase
PYTHONUSERBASE=~/userbase pip install --user ~/dist/compdb-*.whl
PYTHONUSERBASE=~/userbase PATH="$HOME/userbase/bin:$PATH" compdb version
rm -r ~/userbase

# Wheel in virtualenv
# Seems to work out of the box for ubuntu 14:04: with setuptools 2.2
# and pip 1.5.x.
# I assume wheels have support for 'extras_require'
# for longer than source distributions.
virtualenv .venv
source .venv/bin/activate
pip install ~/dist/compdb-*.whl
compdb version
deactivate
rm -r .venv

# pip install source distribution
mkdir ~/userbase
PYTHONUSERBASE=~/userbase pip install --user ~/dist/compdb-*.tar.gz
PYTHONUSERBASE=~/userbase PATH="$HOME/userbase/bin:$PATH" compdb version
rm -r ~/userbase

# pip install source distribution in virtualenv
#
# 2 alternatives:
# pip vendors setuptools, in pip 7.1.0 setuptools has been bumped to version 18.
# Starting from this version 'extras_require' is supported in setup().
#
# 1. works but does not use extras_require
virtualenv .venv
source .venv/bin/activate
pip install -U 'setuptools>=3.3,<18'
pip install -U 'pip<7.1.0'
pip install ~/dist/compdb-*.tar.gz
compdb version
deactivate
rm -r .venv
# 2. works by using extras_require
virtualenv .venv
source .venv/bin/activate
pip install -U 'setuptools>=18'
pip install -U 'pip>=7.1.0'
pip install ~/dist/compdb-*.tar.gz
compdb version
deactivate
rm -r .venv

# requirements.txt, depends on the pip version that vendors setuptools>=18
virtualenv .venv
source .venv/bin/activate
pip install -U 'pip==7.1.0'
pip install -r requirements.txt
deactivate
rm -r .venv
