from __future__ import print_function, unicode_literals, absolute_import

import os
import pprint


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
    """Mimic clang::tooling::CompilationDatabase interface."""

    def get_compile_commands(self, filepath):
        """Get the compile commands for the given file.

        Return an iterable of CompileCommand.
        """
        raise NotImplementedError

    def get_all_files(self):
        """Return an iterable of path strings."""
        raise NotImplementedError

    def get_all_compile_commands(self):
        """Return an iterable of CompileCommand."""
        raise NotImplementedError
