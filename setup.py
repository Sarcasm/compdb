#!/usr/bin/env python
# -*- coding: utf-8 -*-

import setuptools
import sys

from codecs import open
from distutils.version import LooseVersion
from os import path
from setuptools import setup, find_packages

local_path = path.abspath(path.dirname(__file__))

# find_packages()'s 'include' parameter has been introduced in setuptools 3.3.
#
# Ubuntu 14:04 comes with 3.3 for the system wide installation,
# but when using virtualenv the setuptools version is 2.2.
# The solution is to upgrade setuptools in the virtualenv.
if LooseVersion(setuptools.__version__) < LooseVersion('3.3'):
    print("setuptools version:", str(LooseVersion(setuptools.__version__)))
    print("to upgrade with pip, type: pip install -U setuptools")
    raise AssertionError("compdb requires setuptools 3.3 higher")

with open(path.join(local_path, 'README.rst'), encoding='utf-8') as f:
    long_desc = f.read()

about = {}
with open(path.join(local_path, "compdb", "__about__.py")) as f:
    exec(f.read(), about)

install_requires = []
extras_require = {}

# Depending on the setuptools version,
# fill in install_requires or extras_require.
#
# The ideas comes from the following article:
# - https://hynek.me/articles/conditional-python-dependencies/
#
# This handles Ubuntu 14.04, which comes with setuptools 3.3.
# But not everything is handled, a more recent version of setuptools
# is still required to support bdist_wheel.
if LooseVersion(setuptools.__version__) < LooseVersion('18'):
    if "bdist_wheel" in sys.argv:
        print("setuptools version:", str(LooseVersion(setuptools.__version__)))
        print("to upgrade with pip, type: pip install -U setuptools")
        raise AssertionError("setuptools >= 18 required for wheels")
    if sys.version_info[0] < 3:
        install_requires.append('configparser')
else:  # setuptools >= 18
    extras_require[":python_version<'3.0'"] = ['configparser']

setup(
    name=about['__prog__'],
    version=about['__version__'],
    description=about['__desc__'],
    long_description=long_desc,
    url=about['__url__'],
    author=about['__author__'],
    author_email='guillaume.papin@epitech.eu',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    keywords=['Clang', 'compilation-database', 'compdb'],
    packages=find_packages(include=['compdb', 'compdb.*']),
    test_suite="tests",
    entry_points={
        "console_scripts": [
            "compdb=compdb.cli:main",
        ],
    },
    python_requires='>=2.7,!=3.0.*,!=3.1.*,!=3.2.*',
    install_requires=install_requires,
    extras_require=extras_require)
