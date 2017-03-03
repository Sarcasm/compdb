from __future__ import print_function, unicode_literals, absolute_import

import glob
import io
import itertools
import os

import compdb
from compdb.models import (CompilationDatabaseInterface, ProbeError)
from compdb.utils import (suppress, re_fullmatch)
from compdb.db.json import (JSONCompilationDatabase, compile_commands_to_json)


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
            complementer,
            "Invalid complementer name: '{}'".format(complementer.name))


def _chain_get_all_files(databases):
    return itertools.chain.from_iterable((db.get_all_files()
                                          for db in databases))


def _chain_get_all_compile_commands(databases):
    return itertools.chain.from_iterable((db.get_all_compile_commands()
                                          for db in databases))


class _ComplementedDatabase(CompilationDatabaseInterface):
    def __init__(self, directory, base_database):
        self.directory = directory
        self.databases = [base_database]

    def add_complementary_database(self, complementary_database):
        self.databases.append(complementary_database)

    def clear_complementary_databases(self):
        del self.databases[1:]  # all but base_database

    def get_compile_commands(self, filepath):
        for db in self.databases:
            compile_commands = db.get_compile_commands(filepath)
            # The complementary databases aren't supposed to contain files
            # from the main or precedings databases.
            # This allow us to early exit as soon as a match is found.
            if compile_commands:
                return compile_commands
        return iter(())

    def get_all_files(self):
        return _chain_get_all_files(self.databases)

    def get_all_compile_commands(self):
        return _chain_get_all_compile_commands(self.databases)


class _ComplementerWrapper(object):
    def __init__(self, complementer):
        name = complementer.name
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

    def complement(self, compilation_database):
        return self.complementer.complement(compilation_database)


class CompilationDatabase(object):
    def __init__(self):
        self.registry = []
        self.complementers = []
        self.databases = []

    def register_db(self, db_cls):
        if db_cls not in self.registry:
            self.registry.append(db_cls)

    def add_complementer(self, complementer):
        complementer = _ComplementerWrapper(complementer)
        self.complementers.append(complementer)

    def _add_databases(self, databases):
        self.databases.extend(databases)

    def _add_database(self, database):
        self._add_databases([database])

    def _probe_dir1(self, directory):
        for compdb_cls in self.registry:
            with suppress(ProbeError):
                return compdb_cls.probe_directory(directory)
        raise ProbeError(directory)

    def _probe_dir(self, directory):
        database = self._probe_dir1(directory)
        complemented_database = _ComplementedDatabase(directory, database)
        for complementer in self.complementers:
            cache_path = os.path.join(directory, complementer.cache_filename)
            if not os.path.exists(cache_path):
                raise ComplementerCacheNotFound(complementer, directory)
            complemented_database.add_complementary_database(
                JSONCompilationDatabase(cache_path))
        return complemented_database

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
            raise ProbeError(path_pattern)
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
        for db in self.databases:
            db.clear_complementary_databases()
        # incrementally compute the complements,
        # each complement depends on its predecesors
        for complementer in self.complementers:
            yield ('begin', {'complementer': complementer.name})
            for db in self.databases:
                cache_path = os.path.join(db.directory,
                                          complementer.cache_filename)
                yield ('pre-complement', {'file': cache_path})
                compile_commands = complementer.complement(db)
                with io.open(cache_path, 'w', encoding='utf8') as f:
                    compile_commands_to_json(compile_commands, f)
                yield ('post-complement', {'file': cache_path})
                db.add_complementary_database(
                    JSONCompilationDatabase(cache_path))
            yield ('end', {'complementer': complementer.name})

    def get_compile_commands(self, filepath):
        return itertools.chain.from_iterable((db.get_compile_commands(filepath)
                                              for db in self.databases))

    def get_all_files(self):
        return _chain_get_all_files(self.databases)

    def get_all_compile_commands(self):
        return _chain_get_all_compile_commands(self.databases)
