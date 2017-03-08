from __future__ import print_function, unicode_literals, absolute_import

import os
import pprint

import compdb


class ProbeError(LookupError, compdb.CompdbError):
    """Raised when probing a compilation database failed"""

    def __init__(self, message, cause=None):
        super(ProbeError, self).__init__(message)
        self.cause = cause


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


class CompilationDatabaseInterface(object):
    @classmethod
    def probe_directory(cls, directory):
        """Probe compilation database for a specific directory.

        Should return an instance of the compilation database
        if the directory contains a database.
        If the directory does not contain a database,
        a ProbeError should be raised (the default action if not overriden).
        """
        raise ProbeError(
            "{}: compilation databases not found".format(directory))

    def get_compile_commands(self, filepath):
        """Get the compile commands for the given file.

        Return an iterable of CompileCommand.
        """
        raise compdb.NotImplementedError

    def get_all_files(self):
        """Return an iterable of path strings."""
        raise compdb.NotImplementedError

    def get_all_compile_commands(self):
        """Return an iterable of CompileCommand."""
        raise compdb.NotImplementedError
