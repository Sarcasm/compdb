#!/usr/bin/env python
# -*- coding: utf-8 -*-

from codecs import open
from os import path
from setuptools import setup, find_packages

import compdb

local_path = path.abspath(path.dirname(__file__))

with open(path.join(local_path, 'README.rst'), encoding='utf-8') as f:
    long_desc = f.read()

setup(
    name='compdb',
    version=compdb.__version__,
    description='Compilation database utilities',
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
    entry_points={
        "console_scripts": [
            "compdb=compdb:main",
        ],
    },
)
