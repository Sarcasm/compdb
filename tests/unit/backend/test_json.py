from __future__ import print_function, unicode_literals, absolute_import

import os
import unittest

from compdb.backend.json import JSONCompilationDatabase
from compdb.models import CompileCommand


class JSONCompilationDatabaseTest(unittest.TestCase):
    LOCAL_PATH = os.path.abspath(os.path.dirname(__file__))
    TEST_DIR = os.path.join(LOCAL_PATH, 'test_json_data')

    def setUp(self):
        self.db = JSONCompilationDatabase.probe_directory(self.TEST_DIR)

    def tearDown(self):
        self.db = None

    def test_get_compile_commands(self):
        a_commands = list(self.db.get_compile_commands("/tmp/a.cpp"))
        self.assertEqual(len(a_commands), 1)
        self.assertEqual(a_commands[0],
                         CompileCommand("/tmp/", "/tmp/a.cpp",
                                        ["clang", "-DA=1"]))
        b_commands = list(self.db.get_compile_commands("/tmp/b.cpp"))
        self.assertEqual(len(b_commands), 2)
        self.assertEqual(b_commands[0],
                         CompileCommand("/tmp/", "/tmp/b.cpp",
                                        ["clang", "-DB=1"]))
        self.assertEqual(b_commands[1],
                         CompileCommand("/tmp/", "/tmp/b.cpp",
                                        ["clang", "-DB=2"]))
        c_commands = list(self.db.get_compile_commands("/tmp/c.cpp"))
        self.assertEqual(len(c_commands), 1)
        self.assertEqual(c_commands[0],
                         CompileCommand("/tmp/", "/tmp/c.cpp",
                                        ["clang", "-DC=1"], "c.o"))

    def test_get_all_files(self):
        files = list(sorted(self.db.get_all_files()))
        self.assertEqual(
            files,
            [
                '/tmp/a.cpp',
                '/tmp/b.cpp',
                # note: it's debatable whether duplicates should be present
                '/tmp/b.cpp',
                '/tmp/c.cpp',
            ])
