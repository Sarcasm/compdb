from __future__ import print_function, unicode_literals, absolute_import

import glob
import itertools
import os

from compdb.models import ProbeError
from compdb.utils import suppress


class CompilationDatabase(object):
    def __init__(self):
        self.registry = []
        self.databases = []
        self.overlays = []
        self.__overlayed_databases = []

    def register_db(self, db_cls):
        if db_cls not in self.registry:
            self.registry.append(db_cls)

    def register_overlay(self, overlay):
        self.overlays.append(overlay)

    def _probe_dir(self, directory):
        for compdb_cls in self.registry:
            with suppress(ProbeError):
                return compdb_cls.probe_directory(directory)
        raise ProbeError(directory)

    def add_directory(self, directory):
        self.databases.append(self._probe_dir(directory))

    def add_directories(self, directories):
        """Either all directories are added successfuly
        or none if an exception is raised."""
        databases = []
        for directory in directories:
            databases.append(self._probe_dir(directory))
        self.databases.extend(databases)

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
        self.databases.extend(self._add_directory_pattern1(path_pattern))

    def add_directory_patterns(self, path_patterns):
        databases = []
        for path_pattern in path_patterns:
            databases.extend(self._add_directory_pattern1(path_pattern))
        self.databases.extend(databases)

    def update_overlays(self):
        pass

    @property
    def _overlayed_databases(self):
        return self.databases

    def get_compile_commands(self, filepath):
        return itertools.chain.from_iterable(
            (cdb.get_compile_commands(filepath)
             for cdb in self._overlayed_databases))

    def get_all_files(self):
        return itertools.chain.from_iterable(
            (cdb.get_all_files() for cdb in self._overlayed_databases))

    def get_all_compile_commands(self):
        return itertools.chain.from_iterable(
            (cdb.get_all_compile_commands()
             for cdb in self._overlayed_databases))
