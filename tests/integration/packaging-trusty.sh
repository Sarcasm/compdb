#!/bin/bash

# This script tests the packaging of compdb on Ubuntu Trusty.

# It has been made to run on Travis CI and inside docker image of Ubuntu 14.04.
# For the docker image, one can use docker/ubuntu-trusty.sh.
# At this time it is not recommended to run this locally
# because files are created in the user home directory.
# The dependencies can be found in docker/ubuntu-trusty/Dockerfile.

if [[ ! -f compdb/__init__.py ]]; then
    1>&2 echo "error: this script expects to run in compdb root directory!"
    exit 1
fi

set -o errexit
set -o xtrace

# Initial goal for this script was to run in a "pristine" Ubuntu Trusty,
# with a stock installation of python,
# unfortunately Travis CI uses isolated virtualenvs:
# - https://docs.travis-ci.com/user/languages/python/#Travis-CI-Uses-Isolated-virtualenvs
#
# This means, one has to accomodate the 'pip install' commands
# to not use the --user options when run under virtualenv.
# Doing otherwise, triggers the following error:
#     $ pip install --user .
#     Can not perform a '--user' install. User site-packages are not visible in this virtualenv.
#
# virtualenv detection logic copied from pip:
# - https://github.com/pypa/pip/blob/ccd75d4daf7753b6587cffbb1ba52e7dfa5e9915/pip/locations.py#L41-L51
USER_OPTS=""
if python -c 'import sys; sys.exit(hasattr(sys, "real_prefix"))' &&
        python -c 'import sys; sys.exit(sys.prefix != getattr(sys, "base_prefix", sys.prefix))'
then
    USER_OPTS="--user"
fi

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
env PYTHONPATH=$(PYTHONUSERBASE=~/userbase python -m site --user-site) \
    PYTHONUSERBASE=~/userbase \
    python setup.py install --user
env PYTHONPATH=$(PYTHONUSERBASE=~/userbase python -m site --user-site) \
    PYTHONUSERBASE=~/userbase \
    PATH="$HOME/userbase/bin:$PATH" \
    compdb version
rm -r ~/userbase

# Install from source with pip
mkdir ~/userbase
PYTHONUSERBASE=~/userbase pip install ${USER_OPTS} .
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
PYTHONUSERBASE=~/userbase pip install ${USER_OPTS} ~/dist/compdb-*.whl
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
PYTHONUSERBASE=~/userbase pip install ${USER_OPTS} ~/dist/compdb-*.tar.gz
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
