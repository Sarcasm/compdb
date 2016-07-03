#!/usr/bin/env python

from __future__ import print_function

import errno
import imp
import json
import operator
import os
import subprocess
import unittest

__prog__ = os.path.basename(__file__)
if __prog__.endswith('.py'):
    __prog__ = __prog__[:-3]

LOCAL_PATH = os.path.abspath(os.path.dirname(__file__))
COMPDB_EXECUTABLE = os.path.join(LOCAL_PATH, '..', 'compdb')

compdb = imp.load_source('compdb', COMPDB_EXECUTABLE)

#
# Helpers
#

TEST_DIR = os.path.join(LOCAL_PATH, __prog__)
TEST_OUT = os.path.join(LOCAL_PATH, 'out', __prog__)


def headerdb(build_dir):
    return subprocess.Popen(
        [COMPDB_EXECUTABLE, 'headerdb', '-p', build_dir],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE).communicate()


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
    with open(db_path, 'w') as dbf:
        compdb.compile_commands_to_json(compile_commands, dbf)


def run_headerdb(test_dirname, compile_commands):
    '''Return `compdb headerdb` output on the given database.

    The output is returned sorted in the following order: file, directory,
    command.

    Second return value is the standard error output.
    '''
    build_dir = os.path.join(TEST_OUT, test_dirname)
    mkdir_p(build_dir)
    create_database(compile_commands, build_dir)
    outs, errs = headerdb(build_dir)
    compdb_out = json.loads(outs.decode("utf-8"))
    compdb_out.sort(key=operator.itemgetter("file", "directory", "command"))
    return compdb_out, errs.decode("utf-8")

#
# Tests start here
#


class HeaderDB(unittest.TestCase):
    def test_01(self):
        test_dirname = 'test_01'
        compdb_in = [
            compdb.CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-DA=1'],
                file='a.cpp'),
            compdb.CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-DB=1'],
                file='b.cpp'),
        ]
        compdb_out, _ = run_headerdb(test_dirname, compdb_in)
        self.assertEqual(1, len(compdb_out))
        self.assertEqual('a.hpp', compdb_out[0]['file'])
        self.assertEqual('clang++ -DA=1', compdb_out[0]['command'])

    def test_02(self):
        test_dirname = 'test_02'
        compdb_in = [
            compdb.CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-Iinclude', '-DA=1'],
                file='src/a.cpp'),
            compdb.CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-Iinclude', '-DB=1'],
                file='src/b.cpp'),
        ]
        compdb_out, _ = run_headerdb(test_dirname, compdb_in)
        self.assertEqual(2, len(compdb_out))
        self.assertEqual('include/a/a.hpp', compdb_out[0]['file'])
        self.assertEqual('clang++ -Iinclude -DA=1', compdb_out[0]['command'])
        self.assertEqual('include/b/b.hpp', compdb_out[1]['file'])
        self.assertEqual('clang++ -Iinclude -DB=1', compdb_out[1]['command'])


if __name__ == "__main__":
    unittest.main()
