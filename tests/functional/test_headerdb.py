#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import

import contextlib
import errno
import io
import json
import operator
import os
import sys
import unittest

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from compdb.db.json import compile_commands_to_json
from compdb.cli import main
from compdb.models import CompileCommand

LOCAL_PATH = os.path.abspath(os.path.dirname(__file__))

#
# Helpers
#

TEST_DIR = os.path.join(LOCAL_PATH, 'headerdb')
TEST_OUT = os.path.join(LOCAL_PATH, 'test-output', 'headerdb')


@contextlib.contextmanager
def captured_output():
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = StringIO(), StringIO()
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def create_database(compile_commands, build_dir):
    db_path = os.path.join(build_dir, 'compile_commands.json')
    with io.open(db_path, 'w', encoding='utf-8') as dbf:
        compile_commands_to_json(compile_commands, dbf)


def run_headerdb(test_dirname, compile_commands):
    '''Return `compdb headerdb` output on the given database.

    The output is returned sorted in the following order: file, directory,
    command.

    Second return value is the standard error output.
    '''
    build_dir = os.path.join(TEST_OUT, test_dirname)
    mkdir_p(build_dir)
    create_database(compile_commands, build_dir)
    with captured_output() as (stdout, stderr):
        main(['-p', build_dir, 'headerdb'])
    outs = stdout.getvalue()
    errs = stderr.getvalue()
    if errs:
        print(errs)
    compdb_out = json.loads(outs)
    compdb_out.sort(key=operator.itemgetter("file", "directory", "command"))
    return compdb_out


class HeaderDB(unittest.TestCase):
    def test_01(self):
        test_dirname = 'test_01'
        compdb_in = [
            CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-DA=1'],
                file='a.cpp'),
            CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-DB=1'],
                file='b.cpp'),
        ]
        compdb_out = run_headerdb(test_dirname, compdb_in)
        self.assertEqual(1, len(compdb_out))
        self.assertEqual('a.hpp', compdb_out[0]['file'])
        self.assertEqual('clang++ -DA=1', compdb_out[0]['command'])

    def test_02(self):
        test_dirname = 'test_02'
        compdb_in = [
            CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-Iinclude', '-DA=1'],
                file='src/a.cpp'),
            CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-Iinclude', '-DB=1'],
                file='src/b.cpp'),
        ]
        compdb_out = run_headerdb(test_dirname, compdb_in)
        self.assertEqual(2, len(compdb_out))
        self.assertEqual('include/a/a.hpp', compdb_out[0]['file'])
        self.assertEqual('clang++ -Iinclude -DA=1', compdb_out[0]['command'])
        self.assertEqual('include/b/b.hpp', compdb_out[1]['file'])
        self.assertEqual('clang++ -Iinclude -DB=1', compdb_out[1]['command'])

    def test_03(self):
        test_dirname = 'test_03'
        compdb_in = [
            CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-DAB=1'],
                file='a_b.cpp'),
            CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-DA=1'],
                file='a.cpp'),
            CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-DB=1'],
                file='b.cpp'),
        ]
        compdb_out = run_headerdb(test_dirname, compdb_in)
        self.assertEqual(4, len(compdb_out))
        self.assertEqual('a.hpp', compdb_out[0]['file'])
        self.assertEqual('clang++ -DA=1', compdb_out[0]['command'])
        self.assertEqual('a_private.hpp', compdb_out[1]['file'])
        self.assertEqual('clang++ -DA=1', compdb_out[1]['command'])
        self.assertEqual('b.hpp', compdb_out[2]['file'])
        self.assertEqual('clang++ -DB=1', compdb_out[2]['command'])
        self.assertEqual('b_private.hpp', compdb_out[3]['file'])
        self.assertEqual('clang++ -DB=1', compdb_out[3]['command'])

    def test_04(self):
        test_dirname = 'test_04'
        compdb_in = [
            CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-DA=1'],
                file='a.cpp'),
            CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-DB=1'],
                file='b.cpp'),
        ]
        compdb_out = run_headerdb(test_dirname, compdb_in)
        self.assertEqual(4, len(compdb_out))
        self.assertEqual('a.hpp', compdb_out[0]['file'])
        self.assertEqual('clang++ -DA=1', compdb_out[0]['command'])
        self.assertEqual('a.ipp', compdb_out[1]['file'])
        self.assertEqual('clang++ -DA=1', compdb_out[1]['command'])
        self.assertEqual('b.hpp', compdb_out[2]['file'])
        self.assertEqual('clang++ -DB=1', compdb_out[2]['command'])
        self.assertEqual('b.ipp', compdb_out[3]['file'])
        self.assertEqual('clang++ -DB=1', compdb_out[3]['command'])

    def test_05(self):
        test_dirname = 'test_05'
        compdb_in = [
            CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-DLATIN=1'],
                file='latin-1-á.cpp'),
            CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-DUTF=8'],
                file='utf-8-á.cpp'),
        ]
        compdb_out = run_headerdb(test_dirname, compdb_in)
        self.assertEqual(2, len(compdb_out))
        self.assertEqual('latin-1-á.hpp', compdb_out[0]['file'])
        self.assertEqual('clang++ -DLATIN=1', compdb_out[0]['command'])
        self.assertEqual('utf-8-á.hpp', compdb_out[1]['file'])
        self.assertEqual('clang++ -DUTF=8', compdb_out[1]['command'])

    def test_06(self):
        test_dirname = 'test_06'
        compdb_in = [
            CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-Iinclude', '-Iinclude/a'],
                file='a.cpp'),
        ]
        compdb_out = run_headerdb(test_dirname, compdb_in)
        self.assertEqual(1, len(compdb_out))
        self.assertEqual('include/a/a', compdb_out[0]['file'])
        self.assertEqual('clang++ -Iinclude -Iinclude/a',
                         compdb_out[0]['command'])

    def test_07(self):
        test_dirname = 'test_07'
        compdb_in = [
            CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-DA=1', '-I.'],
                file='a.cpp'),
            CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-DB=1', '-I.'],
                file='b.cpp'),
        ]
        compdb_out = run_headerdb(test_dirname, compdb_in)
        self.assertEqual(2, len(compdb_out))
        self.assertEqual('a.hpp', compdb_out[0]['file'])
        self.assertEqual('clang++ -DB=1 -I.', compdb_out[0]['command'])
        self.assertEqual('quoted_a.hpp', compdb_out[1]['file'])
        self.assertEqual('clang++ -DB=1 -I.', compdb_out[1]['command'])
