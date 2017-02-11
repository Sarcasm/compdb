from __future__ import print_function, unicode_literals, absolute_import

import os
import pprint
import sys


class CompileCommand:
    def __init__(self, directory, file, command):
        self.directory = directory
        self.file = file
        self.command = command

    def __repr__(self):
        return "{{directory: {},\nfile: {},\n command: ".format(
            self.directory, self.file) + pprint.pformat(self.command) + "}\n\n"

    def __str__(self):
        return self.__repr__()

    @property
    def normfile(self):
        return os.path.normpath(os.path.join(self.directory, self.file))


class CompilationDatabase(object):
    """Mimic clang::tooling::CompilationDatabase interface"""

    @staticmethod
    def from_directory(directory):
        """Automatically create a CompilationDatabase from build directory."""
        # FIXME: temporary hack for backward compat
        print(
            'WARNING: CompilationDatabase.from_directory() temporarily hacked',
            file=sys.stderr)
        from compdb.db.json import JSONCompilationDatabase
        return JSONCompilationDatabase.from_directory(directory)

    def get_compile_commands(self, filepath):
        """get the compile commands for the given file

        return an iterable of CompileCommand
        """
        raise NotImplementedError()

    def get_all_files(self):
        """return an iterable of path strings"""
        raise NotImplementedError()

    def get_all_compile_commands(self):
        """return an iterable of CompileCommand"""
        raise NotImplementedError()
