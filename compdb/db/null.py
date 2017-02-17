from __future__ import print_function, unicode_literals, absolute_import

from compdb.models import CompilationDatabase


class NullCompilationDatabase(CompilationDatabase):
    """Null object pattern for CompilationDatabase.

    This represents a valid but empty compilation database."""

    @classmethod
    def from_directory(cls, directory):
        return cls()

    def get_compile_commands(self, filepath):
        return iter(())

    def get_all_files(self):
        return iter(())

    def get_all_compile_commands(self):
        return iter(())
