from __future__ import print_function, unicode_literals, absolute_import

import itertools
import json
import os
import pprint
import re
import shlex
import sys


# Check if a generator has at least one element.
#
# Since we don't want to consume the element the function return a tuple.
# The first element is a boolean telling whether or not the generator is empty.
# The second element is a new generator where the first element has been
# put back.
def empty_iterator_wrap(iterator):
    try:
        first = next(iterator)
    except StopIteration:
        return True, None
    return False, itertools.chain([first], iterator)


class CompilationDatabaseRegistry(type):
    def __init__(self, name, bases, nmspc):
        super(CompilationDatabaseRegistry, self).__init__(name, bases, nmspc)
        if not hasattr(self, 'registry'):
            self.registry = set()
        if len(bases) > 0:  # skip the base class
            self.registry.add(self)

    def __iter__(self):
        return iter(self.registry)

    def __str__(self):
        if self in self.registry:
            return self.__name__
        return self.__name__ + ": " + ", ".join([sc.__name__ for sc in self])


if sys.version_info[0] < 3:

    class RegisteredCompilationDatabase():
        __metaclass__ = CompilationDatabaseRegistry
else:
    # Probably a bad idea but the syntax is incompatible in python2
    exec("""class RegisteredCompilationDatabase(
        metaclass=CompilationDatabaseRegistry):
    pass""")


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


class CompilationDatabase(RegisteredCompilationDatabase):
    """Mimic clang::tooling::CompilationDatabase interface"""

    @staticmethod
    def from_directory(directory):
        """Automatically create a CompilationDatabase from build directory."""
        for cdb_cls in CompilationDatabase:
            if cdb_cls == CompilationDatabase:
                # skip ourselves from the class list
                continue
            cdb = cdb_cls.from_directory(directory)
            if cdb:
                return cdb
        return None

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


class JSONCompilationDatabase(CompilationDatabase):
    def __init__(self, json_db_path):
        self.json_db_path = json_db_path

    @classmethod
    def from_directory(cls, directory):
        json_db_path = os.path.join(directory, 'compile_commands.json')
        return cls(json_db_path) if os.path.exists(json_db_path) else None

    def get_compile_commands(self, filepath):
        filepath = os.path.abspath(filepath)
        for elem in self._data:
            if os.path.abspath(os.path.join(elem['directory'], elem[
                    'file'])) == filepath:
                yield self._dict_to_compile_command(elem)

    def get_all_files(self):
        for entry in self._data:
            yield os.path.normpath(
                os.path.join(entry['directory'], entry['file']))

    def get_all_compile_commands(self):
        # PERFORMANCE: I think shlex is inherently slow,
        # something performing better may be necessary
        return list(map(self._dict_to_compile_command, self._data))

    # https://github.com/mozilla/gecko-dev/commit/b54191a5f853a55de05e402b93f1a2ac39cf6355
    # https://bugzilla.mozilla.org/show_bug.cgi?id=1224452
    @staticmethod
    def _dict_to_compile_command(d):
        return CompileCommand(d['directory'], d['file'],
                              shlex.split(d['command']))

    @property
    def _data(self):
        if not hasattr(self, '__data'):
            with open(self.json_db_path) as f:
                self.__data = json.load(f)
        return self.__data


def command_to_json(commands):
    cmd_line = '"'
    for i, command in enumerate(commands):
        if i != 0:
            cmd_line += ' '
        has_space = re.search(r"\s", command) is not None
        # reader now accepts simple quotes, so we need to support them here too
        has_simple_quote = "'" in command
        need_quoting = has_space or has_simple_quote
        if need_quoting:
            cmd_line += r'\"'
        cmd_line += command.replace("\\", r'\\\\').replace(r'"', r'\\\"')
        if need_quoting:
            cmd_line += r'\"'
    return cmd_line + '"'


def str_to_json(s):
    return '"{}"'.format(s.replace("\\", "\\\\").replace('"', r'\"'))


def compile_command_to_json(compile_command):
    return r'''{{
  "directory": {},
  "command": {},
  "file": {}
}}'''.format(
        str_to_json(compile_command.directory),
        command_to_json(compile_command.command),
        str_to_json(compile_command.file))


def compile_commands_to_json(compile_commands, fp):
    """
    Dump Json.

    Parameters
    ----------
    compile_commands : CompileCommand iterable
    fp
        A file-like object, JSON is written to this element.
    """
    fp.write('[\n')
    for i, command in enumerate(compile_commands):
        if i != 0:
            fp.write(',\n\n')
        fp.write(compile_command_to_json(command))
    if compile_commands:
        fp.write('\n')
    fp.write(']\n')
