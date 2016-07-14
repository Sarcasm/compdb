#!/usr/bin/env python

import imp
import os
import unittest
import sys

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

LOCAL_PATH = os.path.abspath(os.path.dirname(__file__))
COMPDB_EXECUTABLE = os.path.join(LOCAL_PATH, '..', 'compdb')

# don't generate python cache file ('compdbc' or __pycache__/) for compdb when
# running the tests
sys.dont_write_bytecode = True

compdb = imp.load_source('compdb', COMPDB_EXECUTABLE)

# command: The compile command executed. After JSON unescaping, this must be a
# valid command to rerun the exact compilation step for the translation unit in
# the environment the build system uses. Parameters use shell quoting and shell
# escaping of quotes, with '"' and '\' being the only special characters. Shell
# expansion is not supported.
#
# -- http://clang.llvm.org/docs/JSONCompilationDatabase.html

COMMAND_TO_JSON_DATA = [
    (['clang++'], r'"clang++"'),
    (['clang++', '-std=c++11'], r'"clang++ -std=c++11"'),
    (['clang++', '-DFOO=a b'], r'"clang++ \"-DFOO=a b\""'),
    (['clang++', '-DFOO="str"'], r'"clang++ -DFOO=\\\"str\\\""'),
    (['clang++', '-DFOO="string with spaces"'],
     r'"clang++ \"-DFOO=\\\"string with spaces\\\"\""'),
    (['clang++', '-DFOO="string with spaces and \\-slash"'],
     r'"clang++ \"-DFOO=\\\"string with spaces and \\\\-slash\\\"\""'),
    (['clang++', "-DBAR='c'"], '"clang++ \\"-DBAR=\'c\'\\""'),
]

COMPILE_COMMANDS_TO_JSON_DATA = (
    [compdb.CompileCommand("/tmp", "foo.cpp", ["clang++"]),
     compdb.CompileCommand("/tmp/bar", "bar.cpp", ["clang++", "-std=c++11"])],
    r"""[
{
  "directory": "/tmp",
  "command": "clang++",
  "file": "foo.cpp"
},

{
  "directory": "/tmp/bar",
  "command": "clang++ -std=c++11",
  "file": "bar.cpp"
}
]
""")

class ToJSON(unittest.TestCase):
    def test_command_to_json(self):
        for tpl in COMMAND_TO_JSON_DATA:
            self.assertEqual(tpl[1], compdb.command_to_json(tpl[0]))

    def test_compile_commands_to_json(self):
        output = StringIO()
        compdb.compile_commands_to_json(COMPILE_COMMANDS_TO_JSON_DATA[0], output)
        self.assertEqual(COMPILE_COMMANDS_TO_JSON_DATA[1], output.getvalue())


if __name__ == "__main__":
    unittest.main()
