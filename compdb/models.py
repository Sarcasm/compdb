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
    def __init__(self, directory, file, arguments, output=None):
        self.directory = directory
        self.file = file
        self.arguments = arguments
        self.output = output

    @property
    def normfile(self):
        return os.path.normpath(os.path.join(self.directory, self.file))

    def __repr__(self):
        return "{{directory: {}, file: {}, arguments: {}, output: {}}}".format(
            repr(self.directory),
            repr(self.file), pprint.pformat(self.arguments), repr(self.output))

    def __str__(self):
        return self.__repr__()

    def _as_tuple(self):
        return (self.directory, self.file, self.arguments, self.output)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._as_tuple() == other._as_tuple()
        return NotImplemented

    def __ne__(self, other):
        return not self == other


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
        """Return an iterable of path strings.

        It is ok to return the same path multiple times
        unless all_files_unique() returns True.
        """
        raise compdb.NotImplementedError

    def all_files_unique(self):
        """Whether or not get_all_files() returns unique paths.

        Override this if get_all_files() is guaranteed to return unique paths,
        this fact can be used for optimization.
        """
        return False

    def get_all_compile_commands(self):
        """Return an iterable of CompileCommand."""
        raise compdb.NotImplementedError
