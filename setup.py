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
    name='compdb',
    version=about['__version__'],
    description='The compilation database Swiss army knife',
    long_description=long_desc,
    url='https://github.com/Sarcasm/compdb',
    author='Guillaume Papin',
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
    ],
    keywords=['Clang', 'compilation-database', 'compdb'],
    packages=find_packages(exclude=['tests']),
    test_suite="tests",
    entry_points={
        "console_scripts": [
            "compdb=compdb.compdb:main",
        ],
    },
    install_requires=dependencies,
)
