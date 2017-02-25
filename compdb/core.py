from __future__ import print_function, unicode_literals, absolute_import

import glob
import itertools
import os

from compdb.models import ProbeError
from compdb.utils import suppress


def _chain_get_compile_commands(databases, filepath):
    return itertools.chain.from_iterable((db.get_compile_commands(filepath)
                                          for db in databases))


def _chain_get_all_files(databases):
    return itertools.chain.from_iterable((db.get_all_files()
                                          for db in databases))


def _chain_get_all_compile_commands(databases):
    return itertools.chain.from_iterable((db.get_all_compile_commands()
                                          for db in databases))


class CompilationDatabase(object):
    def __init__(self):
        self.registry = []
        self.overlays = []
        self.databases = []

    def register_db(self, db_cls):
        if db_cls not in self.registry:
            self.registry.append(db_cls)

    def register_overlay(self, overlay):
        self.overlays.append(overlay)

    def _add_databases(self, databases):
        self.databases.extend(databases)

    def _add_database(self, database):
        self._add_databases([database])

    def _probe_dir(self, directory):
        for compdb_cls in self.registry:
            with suppress(ProbeError):
                return compdb_cls.probe_directory(directory)
        raise ProbeError(directory)

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

    def update_overlays(self):
        pass

    def get_compile_commands(self, filepath):
        return _chain_get_all_compile_commands(self.databases, filepath)

    def get_all_files(self):
        return _chain_get_all_files(self.databases)

    def get_all_compile_commands(self):
        return _chain_get_all_compile_commands(self.databases)
