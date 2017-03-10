# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, absolute_import

import operator
import os
import unittest

from compdb.db.memory import InMemoryCompilationDatabase
from compdb.complementer.headerdb import (
    Complementer,
    subword_split, )
from compdb.models import CompileCommand


class Utils(unittest.TestCase):
    def test_subword_split(self):
        self.assertEqual(["Camel", "Case"], subword_split("CamelCase"))
        self.assertEqual(["camel", "Back"], subword_split("camelBack"))
        self.assertEqual(["String", "Ref"], subword_split("StringRef"))
        self.assertEqual(["Gst", "Buffer"], subword_split("GstBuffer"))
        self.assertEqual(["NS", "String"], subword_split("NSString"))
        self.assertEqual(["ALLCAP"], subword_split("ALLCAP"))
        self.assertEqual(["nocap"], subword_split("nocap"))
        self.assertEqual(["One", "Two", "Three", "Four"],
                         subword_split("OneTwoThreeFour"))
        self.assertEqual(["Foo1", "Bar2"], subword_split("Foo1Bar2"))
        self.assertEqual(["123"], subword_split("123"))
        self.assertEqual(["lowercase", "underscore"],
                         subword_split("lowercase_underscore"))
        self.assertEqual(["Funny", "Case", "dash"],
                         subword_split("FunnyCase-dash"))
        # this one is debatable, we could have empty strings too
        self.assertEqual(["underscore"], subword_split("_underscore_"))
        self.assertEqual(["with", "dot"], subword_split("with.dot"))
        self.assertEqual(["with", "space"], subword_split("with space"))


class HeaderDB(unittest.TestCase):
    LOCAL_PATH = os.path.abspath(os.path.dirname(__file__))
    TEST_DIR = os.path.join(LOCAL_PATH, 'headerdb')

    def srcdir(self, dirname):
        return os.path.join(self.TEST_DIR, dirname)

    def complement(self, compile_commands):
        '''
        The output is returned sorted in the following order: file, directory,
        command.
        '''
        database = InMemoryCompilationDatabase(compile_commands)
        result = list(Complementer().complement([[database]])[0]
                      .get_all_compile_commands())
        result.sort(key=operator.attrgetter('file', 'directory', 'command'))
        return result

    def test_01(self):
        test_srcdir = self.srcdir('test_01')
        result = self.complement([
            CompileCommand(
                directory=test_srcdir,
                command=['clang++', '-DA=1'],
                file='a.cpp'),
            CompileCommand(
                directory=test_srcdir,
                command=['clang++', '-DB=1'],
                file='b.cpp'),
        ])

        self.assertEqual(1, len(result))
        self.assertEqual('a.hpp', result[0].file)
        self.assertEqual(['clang++', '-DA=1'], result[0].command)

    def test_02(self):
        test_srcdir = self.srcdir('test_02')
        result = self.complement([
            CompileCommand(
                directory=test_srcdir,
                command=['clang++', '-Iinclude', '-DA=1'],
                file='src/a.cpp'),
            CompileCommand(
                directory=test_srcdir,
                command=['clang++', '-Iinclude', '-DB=1'],
                file='src/b.cpp'),
        ])
        self.assertEqual(2, len(result))
        self.assertEqual('include/a/a.hpp', result[0].file)
        self.assertEqual(['clang++', '-Iinclude', '-DA=1'], result[0].command)
        self.assertEqual('include/b/b.hpp', result[1].file)
        self.assertEqual(['clang++', '-Iinclude', '-DB=1'], result[1].command)

    def test_03(self):
        test_srcdir = self.srcdir('test_03')
        result = self.complement([
            CompileCommand(
                directory=test_srcdir,
                command=['clang++', '-DAB=1'],
                file='a_b.cpp'),
            CompileCommand(
                directory=test_srcdir,
                command=['clang++', '-DA=1'],
                file='a.cpp'),
            CompileCommand(
                directory=test_srcdir,
                command=['clang++', '-DB=1'],
                file='b.cpp'),
        ])
        self.assertEqual(4, len(result))
        self.assertEqual('a.hpp', result[0].file)
        self.assertEqual(['clang++', '-DA=1'], result[0].command)
        self.assertEqual('a_private.hpp', result[1].file)
        self.assertEqual(['clang++', '-DA=1'], result[1].command)
        self.assertEqual('b.hpp', result[2].file)
        self.assertEqual(['clang++', '-DB=1'], result[2].command)
        self.assertEqual('b_private.hpp', result[3].file)
        self.assertEqual(['clang++', '-DB=1'], result[3].command)

    def test_04(self):
        test_srcdir = self.srcdir('test_04')
        result = self.complement([
            CompileCommand(
                directory=test_srcdir,
                command=['clang++', '-DA=1'],
                file='a.cpp'),
            CompileCommand(
                directory=test_srcdir,
                command=['clang++', '-DB=1'],
                file='b.cpp'),
        ])
        self.assertEqual(4, len(result))
        self.assertEqual('a.hpp', result[0].file)
        self.assertEqual(['clang++', '-DA=1'], result[0].command)
        self.assertEqual('a.ipp', result[1].file)
        self.assertEqual(['clang++', '-DA=1'], result[1].command)
        self.assertEqual('b.hpp', result[2].file)
        self.assertEqual(['clang++', '-DB=1'], result[2].command)
        self.assertEqual('b.ipp', result[3].file)
        self.assertEqual(['clang++', '-DB=1'], result[3].command)

    def test_05(self):
        test_srcdir = self.srcdir('test_05')
        result = self.complement([
            CompileCommand(
                directory=test_srcdir,
                command=['clang++', '-DLATIN=1'],
                file='latin-1-á.cpp'),
            CompileCommand(
                directory=test_srcdir,
                command=['clang++', '-DUTF=8'],
                file='utf-8-á.cpp'),
        ])
        self.assertEqual(2, len(result))
        self.assertEqual('latin-1-á.hpp', result[0].file)
        self.assertEqual(['clang++', '-DLATIN=1'], result[0].command)
        self.assertEqual('utf-8-á.hpp', result[1].file)
        self.assertEqual(['clang++', '-DUTF=8'], result[1].command)

    def test_06(self):
        test_srcdir = self.srcdir('test_06')
        result = self.complement([
            CompileCommand(
                directory=test_srcdir,
                command=['clang++', '-Iinclude', '-Iinclude/a'],
                file='a.cpp'),
        ])
        self.assertEqual(1, len(result))
        self.assertEqual('include/a/a', result[0].file)
        self.assertEqual(['clang++', '-Iinclude', '-Iinclude/a'],
                         result[0].command)

    def test_07(self):
        test_srcdir = self.srcdir('test_07')
        result = self.complement([
            CompileCommand(
                directory=test_srcdir,
                command=['clang++', '-DA=1', '-I.'],
                file='a.cpp'),
            CompileCommand(
                directory=test_srcdir,
                command=['clang++', '-DB=1', '-I.'],
                file='b.cpp'),
        ])
        self.assertEqual(2, len(result))
        self.assertEqual('a.hpp', result[0].file)
        self.assertEqual(['clang++', '-DB=1', '-I.'], result[0].command)
        self.assertEqual('quoted_a.hpp', result[1].file)
        self.assertEqual(['clang++', '-DB=1', '-I.'], result[1].command)


if __name__ == "__main__":
    unittest.main()
