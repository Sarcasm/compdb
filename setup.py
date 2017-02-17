#!/usr/bin/env python
# -*- coding: utf-8 -*-

from codecs import open
from os import path
from setuptools import setup, find_packages
import sys

local_path = path.abspath(path.dirname(__file__))

with open(path.join(local_path, 'README.rst'), encoding='utf-8') as f:
    long_desc = f.read()

about = {}
with open(path.join(local_path, "compdb", "__about__.py")) as f:
    exec(f.read(), about)

dependencies = []

if sys.version_info[0] < 3:
    # Would be nicer in 'extra_require' with an environment marker (PEP 496),
    # but this requires a more recent version of setuptools
    # than provided by Ubuntu 14.04.
    dependencies.append('configparser')

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
        "Programming Language :: Python :: Implementation :: PyPy"
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
    install_requires=dependencies,
)
