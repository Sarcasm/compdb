from __future__ import print_function, unicode_literals, absolute_import

import itertools

from compdb.models import CompilationDatabase


class AggregateCompilationDatabase(CompilationDatabase):
    """Null object pattern for CompilationDatabase.

    This represents a valid but empty compilation database."""

    def __init__(self, databases):
        self.databases = databases

    def get_compile_commands(self, filepath):
        return itertools.chain.from_iterable(
            (cdb.get_compile_commands(filepath) for cdb in self.databases))

    def get_all_files(self):
        return itertools.chain.from_iterable((cdb.get_all_files()
                                              for cdb in self.databases))

    def get_all_compile_commands(self):
        return itertools.chain.from_iterable((cdb.get_all_compile_commands()
                                              for cdb in self.databases))
