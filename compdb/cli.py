from __future__ import print_function, unicode_literals, absolute_import

import argparse
import io
import os
import sys
import textwrap

import compdb.config
import compdb.db.json
import compdb.complementer.headerdb
from compdb.__about__ import (__desc__, __prog__, __version__)
from compdb import (filelist, utils)
from compdb.db.json import JSONCompileCommandSerializer
from compdb.core import CompilationDatabase


# http://python-3-patterns-idioms-test.readthedocs.org/en/latest/Metaprogramming.html#example-self-registration-of-subclasses
class CommandRegistry(type):
    def __init__(self, name, bases, nmspc):
        super(CommandRegistry, self).__init__(name, bases, nmspc)
        if not hasattr(self, 'registry'):
            self.registry = set()
        # keep only leaf classes
        self.registry -= set(bases)
        self.registry.add(self)

    def __iter__(self):
        return iter(sorted(self.registry, key=lambda c: c.name))

    def __str__(self):
        if self in self.registry:
            return self.__name__
        return self.__name__ + ": " + ", ".join([sc.__name__ for sc in self])


if sys.version_info[0] < 3:

    class RegisteredCommand():
        __metaclass__ = CommandRegistry
else:
    # Probably a bad idea but the syntax is incompatible in python2
    exec('class RegisteredCommand(metaclass=CommandRegistry): pass')


class Environment(object):
    def __init__(self):
        self.__complementers = {}

    def register_complementer(self, name, cls):
        self.__complementers[name] = cls

    def get_complementer(self, name):
        return self.__complementers[name]


class CommandBase(RegisteredCommand):
    def __init__(self):
        self.env = None
        self.config = None
        self.args = None
        self._database = None

    def set_env(self, env):
        self.env = env

    def set_config(self, config):
        self.config = config

    def set_args(self, args):
        self.args = args

    def get_database_classes(self):
        return [compdb.db.json.JSONCompilationDatabase]

    def make_unpopulated_database(self):
        db = CompilationDatabase()
        for database_cls in self.get_database_classes():
            db.register_backend(database_cls)
        for complementer_name in (self.config.compdb.complementers or []):
            complementer_cls = self.env.get_complementer(complementer_name)
            db.add_complementer(complementer_name, complementer_cls())
        return db

    def populate_database(self, database):
        try:
            if self.args.build_paths:
                database.add_directories(self.args.build_paths)
            elif self.config.compdb.build_dir:
                database.add_directory_patterns(self.config.compdb.build_dir)
        except compdb.models.ProbeError as e:
            print("error: invalid database(s): {}".format(e), file=sys.stderr)
            sys.exit(1)

    def make_database(self):
        db = self.make_unpopulated_database()
        self.populate_database(db)
        return db


class HelpCommand(CommandBase):
    name = 'help'
    help_short = 'display this help'

    def execute(self):
        print('compdb: {}'.format(__desc__))
        print()
        print('usage: compdb [general options] '
              'command [command options] [command arguments]')
        print()
        print('available commands:')
        command_max_len = max(map(len, [c.name for c in RegisteredCommand]))
        for c in RegisteredCommand:
            print("    {c.name:<{max_len}}   {c.help_short}".format(
                c=c, max_len=command_max_len))


class VersionCommand(CommandBase):
    name = 'version'
    help_short = 'display this version of {}'.format(__prog__)

    @classmethod
    def options(cls, parser):
        parser.add_argument(
            '--short', action='store_true', help='machine readable version')

    def execute(self):
        if self.args.short:
            print(__version__)
        else:
            print(__prog__, "version", __version__)


class ConfigCommand(CommandBase):
    name = 'config'
    help_short = 'get directory and global configuration options'

    @classmethod
    def options(cls, parser):
        # http://stackoverflow.com/a/18283730/951426
        # http://bugs.python.org/issue9253#msg186387
        subparsers = parser.add_subparsers(
            title='available subcommands',
            metavar='<subcommand>',
            dest='subcommand')
        subparsers.dest = 'subcommand'
        # subcommand seems to be required by default in python 2.7 but not 3.5,
        # forcing it to true limit the differences between the two
        subparsers.required = True

        subparser = subparsers.add_parser(
            'print-user-conf',
            help='print the user configuration path',
            formatter_class=SubcommandHelpFormatter)
        subparser.set_defaults(config_func=cls.execute_print_user_conf)

        subparser = subparsers.add_parser(
            'print-local-conf',
            help='print the project local configuration',
            formatter_class=SubcommandHelpFormatter)
        subparser.set_defaults(config_func=cls.execute_print_local_conf)

        subparser = subparsers.add_parser(
            'list',
            help='list all the configuration keys',
            formatter_class=SubcommandHelpFormatter)
        subparser.set_defaults(config_func=cls.execute_list)

        subparser = subparsers.add_parser(
            'dump',
            help='dump effective configuration',
            formatter_class=SubcommandHelpFormatter)
        subparser.set_defaults(config_func=cls.execute_dump)

        subparser = subparsers.add_parser(
            'get',
            help='get configuration variable effective value',
            formatter_class=SubcommandHelpFormatter)
        subparser.set_defaults(config_func=cls.execute_get)
        subparser.add_argument('key', help='the value to get: SECTION.VAR')

    def execute(self):
        self.args.config_func(self)

    def execute_print_user_conf(self):
        print(compdb.config.get_user_conf())

    def execute_print_local_conf(self):
        local_conf = compdb.config.get_local_conf()
        if not local_conf:
            print("error: local configuration not found", file=sys.stderr)
            sys.exit(1)
        print(local_conf)

    def execute_list(self):
        for key in sorted(self.config.options()):
            print(key)

    def execute_get(self):
        section, option = compdb.config.parse_key(self.args.key)
        section = getattr(self.config, section)
        print(getattr(section, option))

    def execute_dump(self):
        self.config.get_effective_configuration().write(sys.stdout)


class ListCommand(CommandBase):
    name = 'list'
    help_short = 'list database entries'

    @classmethod
    def options(cls, parser):
        parser.add_argument(
            '-1',
            '--unique',
            action='store_true',
            help='restrict results to a single entry per file')
        parser.add_argument(
            'files', nargs='*', help='restrict results to a list of files')

    def _gen_results(self):
        database = self.make_database()
        for file in self.args.files or [None]:
            if file:
                compile_commands = database.get_compile_commands(
                    file, unique=self.args.unique)
            else:
                compile_commands = database.get_all_compile_commands(
                    unique=self.args.unique)
            yield (file, compile_commands)

    def execute(self):
        has_missing_files = False
        with JSONCompileCommandSerializer(
                utils.stdout_unicode_writer()) as serializer:
            for file, compile_commands in self._gen_results():
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


class UpdateCommand(CommandBase):
    name = 'update'
    help_short = 'update or create complementary databases'

    def execute(self):
        if not self.config.compdb.complementers:
            print(
                'error: no complementers configured '
                '(config compdb.complementers)',
                file=sys.stderr)
            sys.exit(1)

        database = self.make_unpopulated_database()
        database.raise_on_missing_cache = False
        self.populate_database(database)

        for state, update in database.update_complements():
            if state == 'begin':
                print('Start {complementer}:'.format(**update))
            elif state == 'end':
                pass  # no visual feedback on purpose for this one
            elif state == 'saving':
                print("  OUT {file}".format(**update))
            else:
                print("unsupported: {}: {}".format(state, update))


def _get_suppressions_patterns_from_file(path):
    patterns = []
    with io.open(path, 'r', encoding='utf-8') as f:
        for line in f:
            pattern = line.partition('#')[0].rstrip()
            if pattern:
                patterns.append(pattern)
    return patterns


def _make_file_scanner(config, args):
    scanner = filelist.FileScanner()
    scanner.add_suppressions(args.suppress)
    scanner.add_suppressions(config.scan_files.suppress or [])
    for supp_file in args.suppressions_file:
        scanner.add_suppressions(
            _get_suppressions_patterns_from_file(supp_file))
    for supp_file in (config.scan_files.suppressions_files or []):
        scanner.add_suppressions(
            _get_suppressions_patterns_from_file(supp_file))
    groups = args.groups.split(',')
    for group in groups:
        scanner.enable_group(group)
    return scanner


class ScanFilesCommand(CommandBase):
    name = 'scan-files'
    help_short = 'scan directory for source files'
    help_detail = """
    Lookup given paths for source files.

    Source files includes C, C++ files, headers, and more.
    """

    @classmethod
    def config_schema(cls, schema):
        schema.register_path_list('suppressions-files',
                                  'files containing suppress patterns')
        schema.register_string_list('suppress',
                                    'ignore files matching these patterns')

    @classmethod
    def options(cls, parser):
        parser.add_argument(
            '--suppress',
            metavar='pattern',
            action='append',
            default=[],
            help='ignore files matching the given pattern')
        parser.add_argument(
            '--suppressions-file',
            metavar='file',
            action='append',
            default=[],
            help='add suppress patterns from file')
        parser.add_argument(
            '-g',
            '--groups',
            help="restrict search to files of the groups [source,header]",
            default="source,header")
        parser.add_argument(
            'path',
            nargs='*',
            default=["."],
            help="search path(s) (default: %(default)s)")

    def execute(self):
        scanner = _make_file_scanner(self.config, self.args)
        # join is to have a path separator at the end
        prefix_to_skip = os.path.join(os.path.abspath('.'), '')
        for path in scanner.scan_many(self.args.path):
            # make descendant paths relative
            if path.startswith(prefix_to_skip):
                path = path[len(prefix_to_skip):]
            print(path)


class CheckCommand(CommandBase):
    name = 'check'
    help_short = 'report files absent from the compilation database(s)'
    help_detail = """
    Report files that are found in the workspace
    but not in the compilation database.
    And files that are in the compilation database
    but not found in the workspace.

    Exit with status 1 if some file in the workspace
    aren't found in the compilation database.
    """

    @classmethod
    def options(cls, parser):
        ScanFilesCommand.options(parser)

    def execute(self):
        scanner = _make_file_scanner(self.config, self.args)
        database = self.make_database()
        db_files = frozenset(database.get_all_files())
        list_files = frozenset(scanner.scan_many(self.args.path))

        # this only is not a hard error, files may be in system paths or build
        # directory for example
        db_only = db_files - list_files
        if db_only:
            self._print_set_summary(db_only, "compilation database(s)")

        list_only = list_files - db_files

        if not list_only:
            sys.exit(0)

        # print difference an exit with error
        self._print_set_summary(list_only, "project(s)")
        print(
            "error: {} file(s) are missing from the compilation database(s)".
            format(len(list_only)),
            file=sys.stderr)
        sys.exit(1)

    @staticmethod
    def _print_set_summary(files, name):
        print("Only in {}:".format(name))
        cwd = os.getcwd()
        for path in sorted(files):
            if path.startswith(cwd):
                pretty_filename = os.path.relpath(path)
            else:
                pretty_filename = path
            print('  {}'.format(pretty_filename))


# remove the redundant metavar from help output
#
#     usage: foo <sub-parser metavar>
#
#     <sub-parser title>:
#       <sub-parser metavar>            # <- remove this
#         command_a      a description
#         command_b      b description
#
# http://stackoverflow.com/a/13429281/951426
class SubcommandHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def _format_action(self, action):
        parts = super(argparse.RawDescriptionHelpFormatter,
                      self)._format_action(action)
        if action.nargs == argparse.PARSER:
            parts = "\n".join(parts.split("\n")[1:])
        return parts


def term_columns():
    columns = 80

    try:
        # can happens in tests, when we redirect sys.stdout to a StringIO
        stdout_fileno = sys.stdout.fileno()
    except (AttributeError, io.UnsupportedOperation):
        # fileno() is an AttributeError on Python 2 for StringIO.StringIO
        # and io.UnsupportedOperation in Python 3 for io.StringIO
        stdout_fileno = None

    if stdout_fileno is not None and os.isatty(stdout_fileno):
        try:
            columns = int(os.environ["COLUMNS"])
        except (KeyError, ValueError):
            try:
                import fcntl, termios, struct  # noqa: E401
                columns = struct.unpack(
                    'HHHH',
                    fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ,
                                struct.pack('HHHH', 0, 0, 0, 0)))[1]
            except (ImportError, IOError):
                pass
    return columns


def _wrap_paragraphs(text, max_width=None):
    paragraph_width = term_columns()
    if max_width and paragraph_width > max_width:
        paragraph_width = max_width
    if paragraph_width > 2:
        paragraph_width -= 2
    paragraphs = text.split('\n\n')
    return "\n\n".join(
        [textwrap.fill(p.strip(), width=paragraph_width) for p in paragraphs])


def setup(env):
    env.register_complementer('headerdb',
                              compdb.complementer.headerdb.Complementer)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='{}.'.format(__desc__),
        formatter_class=SubcommandHelpFormatter)

    parser.add_argument(
        '-c',
        dest='config_overrides',
        metavar='NAME[=VALUE]',
        action='append',
        default=[],
        help='set value of configuration variable NAME for this invocation')
    parser.add_argument(
        '-p',
        dest='build_paths',
        metavar="BUILD-DIR",
        action='append',
        default=[],
        help='build path(s)')

    # http://stackoverflow.com/a/18283730/951426
    # http://bugs.python.org/issue9253#msg186387
    subparsers = parser.add_subparsers(
        title='available commands', metavar='<command>', dest='command')
    subparsers.dest = 'command'
    # subcommand seems to be required by default in python 2.7 but not 3.5,
    # forcing it to true limit the differences between the two
    subparsers.required = True

    env = Environment()
    setup(env)

    config_schema = compdb.config.ConfigSchema()
    compdb_schema = config_schema.get_section_schema('compdb')
    compdb_schema.register_glob_list('build-dir', 'the build directories')
    compdb_schema.register_string_list('complementers', 'complementers to use')
    for command_cls in RegisteredCommand:
        command_description = command_cls.help_short.capitalize()
        if not command_description.endswith('.'):
            command_description += "."

        # Format detail description, line wrap manually so that unlike the
        # default formatter_class used for subparser we can have
        # newlines/paragraphs in the detailed description.
        if hasattr(command_cls, 'help_detail'):
            command_description += "\n\n"
            command_description += textwrap.dedent(command_cls.help_detail)

        command_description = textwrap.dedent("""
        description:
        """) + _wrap_paragraphs(command_description, 120)

        subparser = subparsers.add_parser(
            command_cls.name,
            formatter_class=SubcommandHelpFormatter,
            help=command_cls.help_short,
            epilog=command_description)
        if callable(getattr(command_cls, 'options', None)):
            command_cls.options(subparser)
        if callable(getattr(command_cls, 'config_schema', None)):
            section_schema = config_schema.get_section_schema(command_cls.name)
            command_cls.config_schema(section_schema)
        subparser.set_defaults(cls=command_cls)

    # if no option is specified we default to "help" so we have something
    # useful to show to the user instead of an error because of missing
    # subcommand
    args = parser.parse_args(argv or sys.argv[1:] or ["help"])
    config = compdb.config.LazyTypedConfig(config_schema)

    if args.config_overrides:
        # config_overrides is a list of tuples: (var, value)
        config_overrides = []
        for override in args.config_overrides:
            var, sep, value = override.partition('=')
            if not sep:
                value = 'yes'
            config_overrides.append((var, value))
        config.set_overrides(config_overrides)

    command = args.cls()
    command.set_env(env)
    command.set_config(config)
    command.set_args(args)

    command.execute()
