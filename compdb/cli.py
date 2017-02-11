from __future__ import print_function, unicode_literals, absolute_import

import argparse
import codecs
import fnmatch
import io
import itertools
import os
import sys
import textwrap

from compdb.__about__ import (
    __desc__,
    __prog__,
    __version__, )

from compdb.models import CompilationDatabase
from compdb import (filelist, headerdb)
import compdb.db.json
import compdb.config


# The issue this function tries to solve is to have a text writer where unicode
# data can be written without decoding error. It should work in the following
# conditions:
# - python 2 & 3, output to terminal
# - python 2 & 3, output to a pipe or shell redirection
#
# When using python 2, if the program output is redirected to a pipe or file,
# the output encoding may be set to 'ascii',
# potentially producing UnicodeEncodeError.
# Redirections do not seem to cause such issue with python 3
# but explicit utf-8 encoding seems a sensible choice to output data to be
# consumed by other programs (e.g: JSON).
#
# XXX: maybe using a io.TextIOBase would be more appropriate?
def get_utf8_writer():
    """Get unicode writer to output UTF-8 encoded data.

    To be used for JSON dump and alike.

    """
    if sys.version_info[0] < 3:
        return codecs.getwriter('utf-8')(sys.stdout)
    return codecs.getwriter('utf-8')(sys.stdout.buffer)


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


class CommandBase(RegisteredCommand):
    pass


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
        for section_name, section_schema in sorted(
                self.config._config_schema._section_to_schemas.items()):
            for key in section_schema.schemas:
                print('{}.{}'.format(section_name, key))

    def execute_dump(self):
        self.config.get_config().write(sys.stdout)

    def execute_get(self):
        section, option = compdb.config.parse_key(self.args.key)
        section = getattr(self.config, section)
        print(getattr(section, option))


class DumpCommand(CommandBase):
    name = 'dump'
    help_short = 'dump the compilation database(s)'

    @classmethod
    def options(cls, parser):
        parser.add_argument(
            '-p',
            metavar="BUILD-DIR",
            help='build path(s)',
            action='append',
            required=True)

    def execute(self):
        cdbs = []
        for build_dir in self.args.p:
            cdb = CompilationDatabase.from_directory(build_dir)
            if not cdb:
                sys.stderr.write('error: compilation database not found\n')
                sys.exit(1)
            cdbs.append(cdb)
        compdb.db.json.compile_commands_to_json(
            itertools.chain.from_iterable(
                [cdb.get_all_compile_commands() for cdb in cdbs]),
            get_utf8_writer())


class FindCommand(CommandBase):
    name = 'find'
    help_short = 'find compile command(s) for a file'
    help_detail = 'Exit with status 1 if no compile command is found.'

    @classmethod
    def options(cls, parser):
        parser.add_argument(
            '-p', metavar="BUILD-DIR", help='build path', required=True)
        parser.add_argument(
            'file', help="file to search for in the compilation database")

    def execute(self):
        build_dir = self.args.p
        cdb = CompilationDatabase.from_directory(build_dir)
        if not cdb:
            sys.stderr.write('error: compilation database not found\n')
            sys.exit(1)
        is_empty, compile_commands = compdb.compdb.empty_iterator_wrap(
            cdb.get_compile_commands(self.args.file))
        if is_empty:
            sys.exit(1)
        compdb.db.json.compile_commands_to_json(compile_commands,
                                                get_utf8_writer())


class HeaderDbCommand(CommandBase):
    name = 'headerdb'
    help_short = 'generate header compilation database from compile command(s)'
    help_detail = """
    Generate a compilation database on the standard output.
    This compilation database is a guess of compile options.

    Exit with status 1 if no compilation database is found.
    """

    @classmethod
    def options(cls, parser):
        parser.add_argument(
            '-p', metavar="BUILD-DIR", help='build path', required=True)

    def execute(self):
        build_dir = self.args.p
        cdb = CompilationDatabase.from_directory(build_dir)
        if not cdb:
            sys.stderr.write('error: compilation database not found\n')
            sys.exit(1)
        headerdb.make_headerdb(cdb.get_all_compile_commands(),
                               get_utf8_writer())


class ScanFilesCommand(CommandBase):
    name = 'scan-files'
    help_short = 'scan directory for source files'
    help_detail = """
    Lookup given paths for source files.

    Source files includes C, C++ files, headers, and more.
    """

    @classmethod
    def options(cls, parser):
        parser.add_argument(
            'path',
            nargs='*',
            default=["."],
            help="search path(s) (default: %(default)s)")
        parser.add_argument(
            '-g',
            '--groups',
            help="restrict search to files of the groups [source,header]",
            default="source,header")

    def execute(self):
        groups = self.args.groups.split(',')
        # join is to have a path separator at the end
        prefix_to_skip = os.path.join(os.path.abspath('.'), '')
        for path in filelist.list_files(groups, self.args.path):
            # make descendant paths relative
            if path.startswith(prefix_to_skip):
                path = path[len(prefix_to_skip):]
            print(path)


class CheckDbCommand(CommandBase):
    name = 'check-db'
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
        parser.add_argument(
            '-p',
            metavar="BUILD-DIR",
            help='build path(s)',
            action='append',
            required=True)
        parser.add_argument(
            'path',
            nargs='*',
            default=["."],
            help="search path(s) (default: %(default)s)")
        parser.add_argument(
            '-g',
            '--groups',
            help="restrict search to files of the groups [source,header]",
            default="source,header")
        parser.add_argument(
            '--suppressions',
            action='append',
            default=[],
            help='add suppression file')

    def execute(self):
        suppressions = []
        for supp in self.args.suppressions:
            suppressions.extend(
                self._get_suppressions_patterns_from_file(supp))

        databases = []
        for build_dir in self.args.p:
            cdb = CompilationDatabase.from_directory(build_dir)
            if not cdb:
                sys.stderr.write('error: compilation database not found\n')
                sys.exit(1)
            databases.append(cdb)

        groups = self.args.groups.split(',')
        db_files = frozenset(
            itertools.chain.from_iterable(
                [cdb.get_all_files() for cdb in databases]))
        list_files = frozenset(filelist.list_files(groups, self.args.path))

        # this only is not a hard error, files may be in system paths or build
        # directory for example
        db_only = db_files - list_files
        if db_only:
            self._print_set_summary(db_only, "compilation database(s)")

        list_only = list_files - db_files
        # filter out suppressions
        # could convert the fnmatch expression to regex and use re.search()
        # instead of prefixing */ pattern
        suppressions = ['*/{}'.format(supp) for supp in suppressions]
        for supp in suppressions:
            filterred = set(fnmatch.filter(list_only, supp))
            list_only -= filterred

        if not list_only:
            sys.exit(0)

        # print difference an exit with error
        self._print_set_summary(list_only, "project(s)")
        print(
            "error: some files are missing from the compilation database(s)",
            file=sys.stderr)
        sys.exit(1)

    @staticmethod
    def _get_suppressions_patterns_from_file(path):
        patterns = []
        with io.open(path, 'r', encoding='utf-8') as f:
            for line in f:
                pattern = line.partition('#')[0].rstrip()
                if pattern:
                    patterns.append(pattern)
        return patterns

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

    if os.isatty(sys.stdout.fileno()):
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


def wrap_paragraphs(text, max_width=None):
    paragraph_width = term_columns()
    if max_width and paragraph_width > max_width:
        paragraph_width = max_width
    if paragraph_width > 2:
        paragraph_width -= 2
    paragraphs = text.split('\n\n')
    return "\n\n".join(
        map(lambda s: textwrap.fill(s.strip(), width=paragraph_width),
            paragraphs))


def main():
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

    # http://stackoverflow.com/a/18283730/951426
    # http://bugs.python.org/issue9253#msg186387
    subparsers = parser.add_subparsers(
        title='available commands', metavar='<command>', dest='command')
    subparsers.dest = 'command'
    # subcommand seems to be required by default in python 2.7 but not 3.5,
    # forcing it to true limit the differences between the two
    subparsers.required = True

    config_schema = compdb.config.ConfigSchema()
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
        """) + wrap_paragraphs(command_description, 120)

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
    args = parser.parse_args(sys.argv[1:] or ["help"])
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
    command.config = config
    command.args = args
    command.execute()
