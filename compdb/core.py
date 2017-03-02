from __future__ import print_function, unicode_literals, absolute_import

import glob
import io
import itertools
import os

import compdb
from compdb.models import (CompilationDatabaseInterface, ProbeError)
from compdb.utils import (suppress, re_fullmatch)
from compdb.db.json import (JSONCompilationDatabase, compile_commands_to_json)


class DatabaseOverlayError(compdb.CompdbError):
    '''Base exception for overlay-related errors'''

    def __init__(self, overlay, message):
        super(DatabaseOverlayError, self).__init__(message)
        self.overlay = overlay


class DatabaseOverlayNotFound(DatabaseOverlayError):
    def __init__(self, overlay, directory):
        super(DatabaseOverlayNotFound, self).__init__(
            overlay, "Could not find '{}' overlay in '{}'".format(overlay.name,
                                                                  directory))
        self.directory = directory


class DatabaseOverlayNameError(DatabaseOverlayError):
    def __init__(self, overlay):
        super(DatabaseOverlayNameError, self).__init__(
            overlay, "Invalid overlay name: '{}'".format(overlay.name))


def _chain_get_all_files(databases):
    return itertools.chain.from_iterable((db.get_all_files()
                                          for db in databases))


def _chain_get_all_compile_commands(databases):
    return itertools.chain.from_iterable((db.get_all_compile_commands()
                                          for db in databases))


class _OverlayedDb(CompilationDatabaseInterface):
    def __init__(self, directory, base_database):
        self.directory = directory
        self.databases = [base_database]

    def add_overlay(self, overlay_database):
        self.databases.append(overlay_database)

    def clear_overlays(self):
        del self.databases[1:]  # all but base_database

    def get_compile_commands(self, filepath):
        # the overlays aren't supposed to contain files from the main database
        # or preceding overlays
        for db in self.databases:
            compile_commands = db.get_compile_commands(filepath)
            if compile_commands:
                return compile_commands
        return iter(())

    def get_all_files(self):
        return _chain_get_all_files(self.databases)

    def get_all_compile_commands(self):
        return _chain_get_all_compile_commands(self.databases)


class _DatabaseOverlayWrapper(object):
    def __init__(self, database_overlay):
        name = database_overlay.name
        if not self._valid_name(name):
            raise DatabaseOverlayNameError(database_overlay)
        self.name = name
        self.ov = database_overlay

    @staticmethod
    def _valid_name(name):
        return re_fullmatch('[a-z][a-z0-9]*(?:_[a-z0-9]+)*', name)

    @property
    def filename(self):
        return self.name + '.json'

    def compute(self, compilation_database):
        return self.ov.compute(compilation_database)


class CompilationDatabase(object):
    def __init__(self):
        self.registry = []
        self.overlays = []
        self.databases = []

    def register_db(self, db_cls):
        if db_cls not in self.registry:
            self.registry.append(db_cls)

    def register_overlay(self, overlay):
        ov = _DatabaseOverlayWrapper(overlay)
        self.overlays.append(ov)

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
        overlayed_database = _OverlayedDb(directory, database)
        for ov in self.overlays:
            ov_path = os.path.join(directory, ov.filename)
            if not os.path.exists(ov_path):
                raise DatabaseOverlayNotFound(ov, directory)
            overlayed_database.add_overlay(JSONCompilationDatabase(ov_path))
        return overlayed_database

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
        for db in self.databases:
            db.clear_overlays()
        for overlay in self.overlays:
            for db in self.databases:
                compile_commands = overlay.compute(db)
                ovdb_path = os.path.join(db.directory, overlay.filename)
                yield ('pre-update', {'file': ovdb_path})
                with io.open(ovdb_path, 'w', encoding='utf8') as f:
                    compile_commands_to_json(compile_commands, f)
                yield ('post-update', {'file': ovdb_path})
                db.add_overlay(JSONCompilationDatabase(ovdb_path))

    def get_compile_commands(self, filepath):
        return itertools.chain.from_iterable((db.get_compile_commands(filepath)
                                              for db in self.databases))

    def get_all_files(self):
        return _chain_get_all_files(self.databases)

    def get_all_compile_commands(self):
        return _chain_get_all_compile_commands(self.databases)
