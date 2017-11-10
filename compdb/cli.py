from __future__ import print_function, unicode_literals, absolute_import

import argparse
import logging
import os
import sys

import compdb.backend.json
import compdb.includedb
import compdb.utils as utils

from compdb.__about__ import (__prog__, __version__)
from compdb.backend.json import JSONCompileCommandSerializer
from compdb.core import CompilationDatabase


class Config(object):
    def __init__(self):
        self.build_directory_patterns = []

    @property
    def compdb_dir(self):
        # 1. check provided as command line flag --compdb-dir=<dir>
        # 2. check provided by environment variable $COMPDB_DIR
        # 3. locate .compdb directory by walking up filesystem
        # 4. walk up filesystem
        #    - probe db from curdir: e.g. compile_commands.json
        #    - or from build directories specified in global config: e.g.
        #      build/compile_commands.json
        #
        # TODO: CompilationDatabase.probe_directory()
        return utils.locate_dominating_file('compile_commands.json')


class Command(object):
    def execute(self, config, args):
        raise NotImplementedError


class HelpCommand(Command):
    name = 'help'
    help_short = 'show general or command help'

    def execute(self, config, argv):
        parser = argparse.ArgumentParser(
            prog='{} {}'.format(__prog__, self.name),
            description=self.help_short)
        parser.add_argument(
            'command',
            nargs='?',
            help='show help information for COMMAND, i.e. '
            '`compdb COMMAND --help`')
        args = parser.parse_args(argv)
        command_registry = CommandRegistry(config)
        if args.command:
            try:
                command_cls = command_registry.get(args.command)
            except:
                parser.error('unrecognized command: {}'.format(args.command))
            command = command_cls()
            command.execute(config, ['--help'])
        else:
            # `compdb help` calls `compdb --help`
            main(['--help'])


class ListCommand(Command):
    name = 'list'
    help_short = 'list database entries'

    def execute(self, config, argv):
        parser = argparse.ArgumentParser(
            prog='{} {}'.format(__prog__, self.name),
            description=self.help_short)
        parser.add_argument(
            '-1',
            '--unique',
            action='store_true',
            help='restrict results to a single entry per file')
        parser.add_argument(
            'files',
            metavar='file',
            nargs='*',
            help='restrict results to a list of files')
        args = parser.parse_args(argv)
        has_missing_files = False
        database = self._make_database(config)
        builder = compdb.includedb.IncludeIndexBuilder()
        included_by_database = builder.build(database)
        with JSONCompileCommandSerializer(
                utils.stdout_unicode_writer()) as serializer:
            for file, compile_commands in self._gen_results(
                    database, included_by_database, args):
                has_compile_command = False
                for compile_command in compile_commands:
                    serializer.serialize(compile_command)
                    has_compile_command = True
                if file and not has_compile_command:
                    print(
                        'error: {}: no such entry'.format(file),
                        file=sys.stderr)
                    has_missing_files = True
        if has_missing_files:
            sys.exit(1)

    def _make_database(self, config):
        backend_registry = BackendRegistry(config)
        database = CompilationDatabase()
        for database_cls in backend_registry.iter():
            database.register_backend(database_cls)
        try:
            if config.build_directory_patterns:
                database.add_directory_patterns(
                    config.build_directory_patterns)
            else:
                database.add_directory(config.compdb_dir)
        except compdb.models.ProbeError as e:
            print(
                "{} {}: error: invalid database(s): {}".format(
                    __prog__, self.name, e),
                file=sys.stderr)
            sys.exit(1)
        return database

    def _gen_results(self, database, included_by_database, args):
        if not args.files:
            yield (None, database.get_all_compile_commands(unique=args.unique))
            yield (None, included_by_database.get_all_compile_commands())
            return
        for file in args.files:
            compile_commands = database.get_compile_commands(
                file, unique=args.unique)
            is_empty, compile_commands = utils.empty_iterator_wrap(
                compile_commands)
            if is_empty:
                path = os.path.abspath(file)
                compile_commands = included_by_database.get_compile_commands(
                    path)
            yield (file, compile_commands)


class VersionCommand(Command):
    name = 'version'
    help_short = 'display this version of {}'.format(__prog__)

    def execute(self, config, argv):
        parser = argparse.ArgumentParser(
            prog='{} {}'.format(__prog__, self.name),
            description=self.help_short)
        parser.add_argument(
            '--short', action='store_true', help='machine readable version')
        args = parser.parse_args(argv)
        if args.short:
            print(__version__)
        else:
            print(__prog__, "version", __version__)


class CommandRegistry(object):
    def __init__(self, config):
        self.config = config

    def _builtins(self):
        return [
            HelpCommand,
            ListCommand,
            VersionCommand,
        ]

    def get(self, name):
        '''Get command class by name.'''
        for command in self._builtins():
            if command.name == name:
                return command
        raise KeyError(name)

    def iter_unique(self):
        '''Iterate over the commands.

        The iteration is done in order: builtin commands first.
        Duplicates are removed.
        '''
        for command in self._builtins():
            yield command
        # compdb entry points
        # example:
        # https://github.com/python-babel/babel/blob/2f599938b3635dd9b91608fa12d5affb0a743052/babel/messages/extract.py#L301
        # import pkg_resources
        # for entry_point in \
        #       pkg_resources.iter_entry_points('compdb_commands'):
        #     yield entry_point.name, entry_point.load()
        # compdb binaries: how to get short description?
        # extract from `compdb-foo --help` if it starts with:
        #     compdb <binary-name>: <oneline description>
        #
        #     usage:
        # then compdb-foo binaries


class BackendRegistry(object):
    def __init__(self, config):
        self.config = config

    def _builtins(self):
        return [
            compdb.backend.json.JSONCompilationDatabase,
        ]

    def iter(self):
        for backend in self._builtins():
            yield backend


def show_help(parser, command_registry):
    parser.print_help()
    print()
    print('available commands:')
    all_commands = list(
        sorted(command_registry.iter_unique(), key=lambda c: c.name))
    max_len = max(map(len, [c.name for c in all_commands]))
    for c in all_commands:
        print("  {c.name:<{max_len}}  {c.help_short}".format(
            c=c, max_len=max_len))


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog=__prog__,
        description='%(prog)s: the compilation database Swiss army knife',
        usage='%(prog)s [general options] '
        'command [command options] [command arguments]',
        add_help=False)
    group = parser.add_argument_group('general options')
    group.add_argument(
        '-h',
        '--help',
        dest='help',
        action='store_true',
        help='show this help message and exit')
    group.add_argument(
        '--debug',
        help="turn on debug logs for the specified modules",
        dest="loggers_to_debug",
        metavar='MODULE',
        action='append',
        default=[])
    group.add_argument(
        '--trace',
        dest='loglevel',
        action='store_const',
        const=logging.INFO,
        help='trace execution')
    group.add_argument(
        '-p',
        dest='build_paths',
        metavar="BUILD_DIR",
        action='append',
        default=[],
        help='build path(s)')
    parser.add_argument('command', nargs='?', help=argparse.SUPPRESS)
    parser.add_argument(
        'args', nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    args = parser.parse_args(argv)

    logging.basicConfig(level=args.loglevel or logging.WARNING)
    for logger_name in args.loggers_to_debug:
        logging.getLogger(logger_name).setLevel(logging.DEBUG)

    config = Config()
    config.build_directory_patterns.extend(args.build_paths)

    command_registry = CommandRegistry(config)

    if args.help:
        show_help(parser, command_registry)
        return

    if args.command is None:
        # TODO: short help, welcome screen, detection info?
        print("compdb-dir: {}\n\n---\n".format(config.compdb_dir))
        args.command = 'help'
        args.args = []

    try:
        command_cls = command_registry.get(args.command)
    except KeyError:
        parser.error('unrecognized command: {}'.format(args.command))

    command = command_cls()
    command.execute(config, args.args)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
