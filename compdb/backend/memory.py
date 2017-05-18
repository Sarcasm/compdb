from __future__ import print_function, unicode_literals, absolute_import

import os

from compdb.models import CompilationDatabaseInterface


class InMemoryCompilationDatabase(CompilationDatabaseInterface):
    def __init__(self, compile_commands=None):
        if compile_commands is None:
            self.compile_commands = []
        else:
            self.compile_commands = compile_commands

    def get_compile_commands(self, filepath):
        filepath = os.path.abspath(filepath)
        for compile_command in self.compile_commands:
            if compile_command.normfile == filepath:
                yield compile_command

    def get_all_files(self):
        return (c.normfile for c in self.compile_commands)

    def get_all_compile_commands(self):
        return iter(self.compile_commands)
