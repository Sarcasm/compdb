#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

import errno
import imp
import json
import operator
import os
import subprocess
import sys
import unittest

__prog__ = os.path.basename(__file__)
if __prog__.endswith('.py'):
    __prog__ = __prog__[:-3]

LOCAL_PATH = os.path.abspath(os.path.dirname(__file__))
COMPDB_EXECUTABLE = os.path.join(LOCAL_PATH, '..', 'compdb')

# don't generate python cache file ('compdbc' or __pycache__/) for compdb when
# running the tests
sys.dont_write_bytecode = True

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


class Utils(unittest.TestCase):
    def test_subword_split(self):
        self.assertEqual(["Camel", "Case"], compdb.subword_split("CamelCase"))
        self.assertEqual(["camel", "Back"], compdb.subword_split("camelBack"))
        self.assertEqual(["String", "Ref"], compdb.subword_split("StringRef"))
        self.assertEqual(["Gst", "Buffer"], compdb.subword_split("GstBuffer"))
        self.assertEqual(["NS", "String"], compdb.subword_split("NSString"))
        self.assertEqual(["ALLCAP"], compdb.subword_split("ALLCAP"))
        self.assertEqual(["nocap"], compdb.subword_split("nocap"))
        self.assertEqual(["One", "Two", "Three", "Four"],
                         compdb.subword_split("OneTwoThreeFour"))
        self.assertEqual(["Foo1", "Bar2"], compdb.subword_split("Foo1Bar2"))
        self.assertEqual(["123"], compdb.subword_split("123"))
        self.assertEqual(["lowercase", "underscore"],
                         compdb.subword_split("lowercase_underscore"))
        self.assertEqual(["Funny", "Case", "dash"],
                         compdb.subword_split("FunnyCase-dash"))
        # this one is debatable, we could have empty strings too
        self.assertEqual(["underscore"], compdb.subword_split("_underscore_"))
        self.assertEqual(["with", "dot"], compdb.subword_split("with.dot"))
        self.assertEqual(["with", "space"], compdb.subword_split("with space"))


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

    def test_03(self):
        test_dirname = 'test_03'
        compdb_in = [
            compdb.CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-DAB=1'],
                file='a_b.cpp'),
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
            compdb.CompileCommand(
                directory=os.path.join(TEST_DIR, test_dirname),
                command=['clang++', '-DYAY=1'],
                file='ČeskýÁČĎÉĚÍŇÓŘŠŤÚŮÝŽáčďéěíňóřšťúůýž.cpp'),
        ]
        compdb_out, _ = run_headerdb(test_dirname, compdb_in)
        self.assertEqual(1, len(compdb_out))
        self.assertEqual('ČeskýÁČĎÉĚÍŇÓŘŠŤÚŮÝŽáčďéěíňóřšťúůýž.hpp',
                         compdb_out[0]['file'])
        self.assertEqual('clang++ -DYAY=1', compdb_out[0]['command'])

if __name__ == "__main__":
    unittest.main()
