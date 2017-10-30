from __future__ import print_function, unicode_literals, absolute_import

import glob
import io
import itertools
import os

import compdb
from compdb.backend.json import (JSONCompilationDatabase,
                                 compile_commands_to_json)
from compdb.backend.memory import InMemoryCompilationDatabase
from compdb.models import (CompilationDatabaseInterface, ProbeError)
from compdb.utils import (suppress, re_fullmatch, empty_iterator_wrap)


class ComplementerError(compdb.CompdbError):
    '''Base exception for complementer-related errors'''

    def __init__(self, complementer, message):
        super(ComplementerError, self).__init__(message)
        self.complementer = complementer


class ComplementerCacheNotFound(ComplementerError):
    def __init__(self, complementer, directory):
        super(ComplementerCacheNotFound, self).__init__(
            complementer, "Could not find '{}' complementer in '{}'".format(
                complementer.name, directory))
        self.directory = directory


class ComplementerNameError(ComplementerError):
    def __init__(self, complementer):
        super(ComplementerNameError, self).__init__(
            complementer, "Invalid complementer name: '{}'".format(
                complementer.name))


def _chain_get_compile_commands(databases, filepath):
    return itertools.chain.from_iterable((db.get_compile_commands(filepath)
                                          for db in databases))


def _chain_get_all_files(databases):
    return itertools.chain.from_iterable((db.get_all_files()
                                          for db in databases))


def _chain_get_all_compile_commands(databases):
    return itertools.chain.from_iterable((db.get_all_compile_commands()
                                          for db in databases))


class _ComplementerWrapper(object):
    def __init__(self, name, complementer):
        if not self._valid_name(name):
            raise ComplementerNameError(complementer)
        self.name = name
        self.complementer = complementer

    @staticmethod
    def _valid_name(name):
        return re_fullmatch('[a-z][a-z0-9]*(?:_[a-z0-9]+)*', name)

    @property
    def cache_filename(self):
        return self.name + '.json'

    def complement(self, databases):
        return self.complementer.complement(databases)


class CompilationDatabase(object):
    def __init__(self):
        self._registry = []
        self._complementers = []
        self._layers = [[]]
        self._directories = []
        self.raise_on_missing_cache = True

    def register_backend(self, db_cls):
        if db_cls not in self._registry:
            self._registry.append(db_cls)

    def add_complementer(self, name, complementer):
        complementer = _ComplementerWrapper(name, complementer)
        self._complementers.append(complementer)
        self._layers.append([])

    def _add_databases(self, probe_results):
        for complemented_database, directory in probe_results:
            for i, db in enumerate(complemented_database):
                self._layers[i].append(db)
            self._directories.append(directory)

    def _add_database(self, probe_result):
        self._add_databases([probe_result])

    def _probe_dir1(self, directory):
        for compdb_cls in self._registry:
            with suppress(ProbeError):
                yield compdb_cls.probe_directory(directory)
                break
        else:
            # no compilation database found,
            # calling the interface's probe_directory() function
            # should raise a good probe error
            CompilationDatabaseInterface.probe_directory(directory)
            # make sure to raise something,
            # in case probe_directory() no longer asserts
            raise AssertionError
        for complementer in self._complementers:
            cache_path = os.path.join(directory, complementer.cache_filename)
            if os.path.exists(cache_path):
                yield JSONCompilationDatabase(cache_path)
            elif self.raise_on_missing_cache:
                raise ComplementerCacheNotFound(complementer, directory)
            else:
                yield InMemoryCompilationDatabase()

    def _probe_dir(self, directory):
        return (list(self._probe_dir1(directory)), directory)

    def add_directory(self, directory):
        self._add_database(self._probe_dir(directory))

    def add_directories(self, directories):
        """Either all directories are added successfuly
        or none if an exception is raised."""
        databases = []
        for directory in directories:
            databases.append(self._probe_dir(directory))
        self._add_databases(databases)

    def _add_directory_pattern1(self, path_pattern):
        # we are interested only in directories,
        # glob() will list only directories if the pattern ends with os.sep
        dir_pattern = os.path.join(path_pattern, '')
        databases = []
        # sorting makes the order predicatable, reproducible
        for directory in sorted(glob.glob(dir_pattern)):
            with suppress(ProbeError):
                databases.append(self._probe_dir(directory))
        if not databases:
            raise ProbeError(
                "{}: no compilation databases found".format(path_pattern))
        return databases

    def add_directory_pattern(self, path_pattern):
        """If no compilation database is found, a ProbeError is raised."""
        self._add_databases(self._add_directory_pattern1(path_pattern))

    def add_directory_patterns(self, path_patterns):
        databases = []
        for path_pattern in path_patterns:
            databases.extend(self._add_directory_pattern1(path_pattern))
        self._add_databases(databases)

    def update_complements(self):
        # clear all complementary databases but keep the initial database
        del self._layers[1:]
        # incrementally compute the complements,
        # each complement depends on its predecesors
        for complementer in self._complementers:
            yield ('begin', {'complementer': complementer.name})
            layer = complementer.complement(self._layers)
            self._layers.append(layer)
            for db, directory in zip(layer, self._directories):
                cache_path = os.path.join(directory,
                                          complementer.cache_filename)
                yield ('saving', {'file': cache_path})
                with io.open(cache_path, 'w', encoding='utf8') as f:
                    compile_commands_to_json(db.get_all_compile_commands(), f)
            yield ('end', {'complementer': complementer.name})

    def get_compile_commands(self, filepath, **kwargs):
        def uniquify(compile_commands):
            for compile_command in compile_commands:
                yield compile_command
                break

        for key in kwargs:
            assert key in ['unique'], "invalid named argument: {}".format(key)
        ret = iter(())
        for layer in self._layers:
            is_empty, compile_commands = empty_iterator_wrap(
                _chain_get_compile_commands(layer, filepath))
            # The complementary databases aren't supposed to contain files
            # from the main or precedings databases.
            # This allow us to early exit as soon as a match is found.
            if not is_empty:
                ret = compile_commands
                break
        if kwargs.get('unique', False):
            ret = uniquify(ret)
        return ret

    def get_all_files(self):
        return itertools.chain.from_iterable((_chain_get_all_files(layer)
                                              for layer in self._layers))

    def get_all_compile_commands(self, **kwargs):
        def uniquify(compile_commands):
            serialized_files = set()
            for compile_command in compile_commands:
                normpath = compile_command.normfile
                if normpath in serialized_files:
                    continue
                serialized_files.add(normpath)
                yield compile_command

        for key in kwargs:
            assert key in ['unique'], "invalid named argument: {}".format(key)
        ret = itertools.chain.from_iterable(
            (_chain_get_all_compile_commands(layer) for layer in self._layers))
        if kwargs.get('unique', False):
            ret = uniquify(ret)
        return ret
