from __future__ import print_function, unicode_literals, absolute_import

import argparse
import codecs
import fnmatch
import io
import itertools
import json
import os
import pprint
import re
import shlex
import sys
import textwrap

from compdb.__about__ import __version__

import compdb.filelist
import compdb.config

__prog__ = os.path.splitext(os.path.basename(__file__))[0]
__desc__ = '''The compilation database Swiss army knife'''


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


# could be an "interface"
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
        # TODO: user should be able to order the compilation databases
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


# http://python-3-patterns-idioms-test.readthedocs.org/en/latest/Metaprogramming.html#example-self-registration-of-subclasses
class CommandRegistry(type):
    def __init__(self, name, bases, nmspc):
        super(CommandRegistry, self).__init__(name, bases, nmspc)
        if not hasattr(self, 'registry'):
            self.registry = set()
        if len(bases) > 0:  # skip the base class
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


class HelpCommand(RegisteredCommand):
    name = 'help'
    help_short = 'display this help'

    def execute(self, config, args):
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


class VersionCommand(RegisteredCommand):
    name = 'version'
    help_short = 'display this version of {}'.format(__prog__)

    def options(self, parser):
        parser.add_argument(
            '--short', action='store_true', help='machine readable version')

    def execute(self, config, args):
        if args.short:
            print(__version__)
        else:
            print(__prog__, "version", __version__)


class ConfigCommand(RegisteredCommand):
    name = 'config'
    help_short = 'get directory and global configuration options'

    def options(self, parser):
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
        subparser.set_defaults(config_func=self.execute_print_user_conf)

        subparser = subparsers.add_parser(
            'print-local-conf',
            help='print the project local configuration',
            formatter_class=SubcommandHelpFormatter)
        subparser.set_defaults(config_func=self.execute_print_local_conf)

        subparser = subparsers.add_parser(
            'list',
            help='list all the configuration keys',
            formatter_class=SubcommandHelpFormatter)
        subparser.set_defaults(config_func=self.execute_list)

        subparser = subparsers.add_parser(
            'dump',
            help='dump effective configuration',
            formatter_class=SubcommandHelpFormatter)
        subparser.set_defaults(config_func=self.execute_dump)

        subparser = subparsers.add_parser(
            'get',
            help='get configuration variable effective value',
            formatter_class=SubcommandHelpFormatter)
        subparser.set_defaults(config_func=self.execute_get)
        subparser.add_argument('key', help='the value to get: SECTION.VAR')

    def execute(self, config, args):
        args.config_func(config, args)

    def execute_print_user_conf(self, config, args):
        print(compdb.config.get_user_conf())

    def execute_print_local_conf(self, config, args):
        local_conf = compdb.config.get_local_conf()
        if not local_conf:
            print("error: local configuration not found", file=sys.stderr)
            sys.exit(1)
        print(local_conf)

    def execute_list(self, config, args):
        for section_name, section_spec in sorted(
                config._config_spec._section_to_specs.items()):
            for key in section_spec.specs:
                print('{}.{}'.format(section_name, key))

    def execute_dump(self, config, args):
        compdb.config.make_conf().write(sys.stdout)

    def execute_get(self, config, args):
        section, sep, var = args.key.partition('.')
        if not sep:
            print(
                "error: invalid key, should be <section>.<variable>",
                file=sys.stderr)
            sys.exit(1)
        section = getattr(config, section)
        print(getattr(section, var))


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


class DumpCommand(RegisteredCommand):
    name = 'dump'
    help_short = 'dump the compilation database(s)'

    def options(self, parser):
        parser.add_argument(
            '-p',
            metavar="BUILD-DIR",
            help='build path(s)',
            action='append',
            required=True)

    def execute(self, config, args):
        cdbs = []
        for build_dir in args.p:
            cdb = CompilationDatabase.from_directory(build_dir)
            if not cdb:
                sys.stderr.write('error: compilation database not found\n')
                sys.exit(1)
            cdbs.append(cdb)
        compile_commands_to_json(
            itertools.chain.from_iterable([cdb.get_all_compile_commands()
                                           for cdb in cdbs]),
            get_utf8_writer())


class FindCommand(RegisteredCommand):
    name = 'find'
    help_short = 'find compile command(s) for a file'
    help_detail = 'Exit with status 1 if no compile command is found.'

    def options(self, parser):
        parser.add_argument(
            '-p', metavar="BUILD-DIR", help='build path', required=True)
        parser.add_argument(
            'file', help="file to search for in the compilation database")

    def execute(self, config, args):
        build_dir = args.p
        cdb = CompilationDatabase.from_directory(build_dir)
        if not cdb:
            sys.stderr.write('error: compilation database not found\n')
            sys.exit(1)
        is_empty, compile_commands = empty_iterator_wrap(
            cdb.get_compile_commands(args.file))
        if is_empty:
            sys.exit(1)
        compile_commands_to_json(compile_commands, get_utf8_writer())


def sanitize_compile_options(compile_command):
    filename = os.path.splitext(compile_command.file)[1]
    file_norm = compile_command.normfile
    adjusted = []
    i = 0
    command = compile_command.command
    while i < len(command):
        # end of options, skip all positional arguments (source files)
        if command[i] == "--":
            break
        # strip -c
        if command[i] == "-c":
            i += 1
            continue
        # strip -o <output-file> and -o<output-file>
        if command[i].startswith("-o"):
            if command[i] == "-o":
                i += 2
            else:
                i += 1
            continue
        # skip input file
        if command[i].endswith(filename):
            arg_norm = os.path.normpath(
                os.path.join(compile_command.directory, command[i]))
            if file_norm == arg_norm:
                i += 1
                continue
        adjusted.append(command[i])
        i += 1
    return adjusted


def mimic_path_relativity(path, other, default_dir):
    """If 'other' file is relative, make 'path' relative, otherwise make it
    absolute.

    """
    if os.path.isabs(other):
        return os.path.join(default_dir, path)
    if os.path.isabs(path):
        return os.path.relpath(path, default_dir)
    return path


def derive_compile_command(header_file, reference):
    return CompileCommand(
        directory=reference.directory,
        file=mimic_path_relativity(header_file, reference.file,
                                   reference.directory),
        command=sanitize_compile_options(reference))


def get_file_includes(path):
    """Returns a tuple of (quote, filename).

    Quote is one of double quote mark '\"' or opening angle bracket '<'.
    """
    includes = []
    with open(path, "rb") as istream:
        include_pattern = re.compile(
            br'\s*#\s*include\s+(?P<quote>["<])(?P<filename>.+?)[">]')
        for b_line in istream:
            b_match = re.match(include_pattern, b_line)
            if b_match:
                u_quote = b_match.group('quote').decode('ascii')
                try:
                    u_filename = b_match.group('filename').decode('utf-8')
                except UnicodeDecodeError:
                    u_filename = b_match.group('filename').decode('latin-1')
                includes.append((u_quote, u_filename))
    return includes


def extract_include_dirs(compile_command):
    header_search_path = []
    i = 0
    command = sanitize_compile_options(compile_command)
    while i < len(command):
        # -I <dir> and -I<dir>
        if command[i].startswith("-I"):
            if command[i] == "-I":
                i += 1
                header_search_path.append(command[i])
            else:
                header_search_path.append(command[i][2:])
        i += 1
    return [os.path.join(compile_command.directory, p)
            for p in header_search_path]


def get_implicit_header_search_path(compile_command):
    return os.path.dirname(
        os.path.join(compile_command.directory, compile_command.file))


SUBWORD_SEPARATORS_RE = re.compile("[^A-Za-z0-9]")

# The comment is shitty because I don't fully understand what is going.
# Shamelessly stolen, then modified from:
# - http://stackoverflow.com/a/29920015/951426
SUBWORD_CAMEL_SPLIT_RE = re.compile(r"""
.+?                          # capture text instead of discarding (#1)
(
  (?:(?<=[a-z0-9]))          # non-capturing positive lookbehind assertion
  (?=[A-Z])                  # match first uppercase letter without consuming
|
  (?<=[A-Z])                 # an upper char should prefix
  (?=[A-Z][a-z0-9])          # an upper char, lookahead assertion: does not
                             # consume the char
|
$                            # ignore capture text #1
)""", re.VERBOSE)


# FIXME: could probably do better/clearer but it seems to work for the case I
# care about
def subword_split(name):
    """Split name into subword.

    Split camelCase, lowercase_underscore, and alike into an array of word.

    Subword is the vocabulary stolen from Emacs subword-mode:
    https://www.gnu.org/software/emacs/manual/html_node/ccmode/Subword-Movement.html

    """
    words = []
    for camel_subname in re.split(SUBWORD_SEPARATORS_RE, name):
        matches = re.finditer(SUBWORD_CAMEL_SPLIT_RE, camel_subname)
        words.extend([m.group(0) for m in matches])
    return words


# Code shamelessly stolen from: http://stackoverflow.com/a/24547864/951426
def lcsubstring_length(a, b):
    """Find the length of the longuest contiguous subsequence of subwords.

    The name is a bit of a misnomer.

    """
    table = {}
    l = 0
    for i, ca in enumerate(a, 1):
        for j, cb in enumerate(b, 1):
            if ca == cb:
                table[i, j] = table.get((i - 1, j - 1), 0) + 1
                if table[i, j] > l:
                    l = table[i, j]
    return l


def score_other_file(a, b):
    """Score the similarity of the given file to the other file.

    Paths are expected absolute and normalized.
    """
    a_dir, a_filename = os.path.split(os.path.splitext(a)[0])
    a_subwords = subword_split(a_filename)
    b_dir, b_filename = os.path.split(os.path.splitext(b)[0])
    b_subwords = subword_split(b_filename)

    score = 0

    # score subword
    # if a.cpp and b.cpp includes a_private.hpp, a.cpp should score better
    subseq_length = lcsubstring_length(a_subwords, b_subwords)
    score += 10 * subseq_length
    # We also penalize the length of the mismatch
    #
    # For example:
    # include/String.hpp
    # include/SmallString.hpp
    # test/StringTest.cpp
    # test/SmallStringTest.cpp
    #
    # Here we prefer String.hpp to get the compile options of StringTest over
    # the one of SmallStringTest.
    score -= 10 * (len(a_subwords) + len(b_subwords) - 2 * subseq_length)

    if a_dir == b_dir:
        score += 50

    return score


def make_headerdb1(compile_commands_iter, parentdb):
    header_mapping = {}
    for compile_command in compile_commands_iter:
        implicit_search_path = get_implicit_header_search_path(compile_command)
        header_search_paths = extract_include_dirs(compile_command)
        src_file = compile_command.normfile
        for quote, filename in get_file_includes(src_file):
            header_abspath = None
            score = 0
            if quote == '"':
                candidate = os.path.normpath(
                    os.path.join(implicit_search_path, filename))
                if os.path.isfile(candidate):
                    header_abspath = candidate
            if not header_abspath:
                for search_path in header_search_paths:
                    candidate = os.path.normpath(
                        os.path.join(search_path, filename))
                    if os.path.isfile(candidate):
                        header_abspath = candidate
                        break
                else:
                    continue
            norm_abspath = os.path.normpath(header_abspath)
            # skip files already present in the parent database
            if norm_abspath in parentdb:
                continue
            score = score_other_file(src_file, norm_abspath)
            if score > header_mapping.get(norm_abspath, (score - 1, None))[0]:
                header_compile_command = derive_compile_command(
                    norm_abspath, compile_command)
                header_mapping[norm_abspath] = (score, header_compile_command)
    return header_mapping


def make_headerdb(compile_commands_iter, fp):
    # mapping of <header normalized absolute path> -> (score, compile_command)
    headerdb = {}
    db_update = make_headerdb1(compile_commands_iter, headerdb)
    # loop until there is nothing more to resolve
    # we first get the files directly included by the compilation database
    # then the files directly included by these files and so on
    while db_update:
        headerdb.update(db_update)
        db_update = make_headerdb1((cmd for _, cmd in db_update.values()),
                                   headerdb)
    compile_commands_to_json((cmd for _, cmd in headerdb.values()), fp)


class HeaderDbCommand(RegisteredCommand):
    name = 'headerdb'
    help_short = 'generate header compilation database from compile command(s)'
    help_detail = """
    Generate a compilation database on the standard output.
    This compilation database is a guess of compile options.

    Exit with status 1 if no compilation database is found.
    """

    def options(self, parser):
        parser.add_argument(
            '-p', metavar="BUILD-DIR", help='build path', required=True)

    def execute(self, config, args):
        build_dir = args.p
        cdb = CompilationDatabase.from_directory(build_dir)
        if not cdb:
            sys.stderr.write('error: compilation database not found\n')
            sys.exit(1)
        make_headerdb(cdb.get_all_compile_commands(), get_utf8_writer())


class ScanFilesCommand(RegisteredCommand):
    name = 'scan-files'
    help_short = 'scan directory for source files'
    help_detail = """
    Lookup given paths for source files.

    Source files includes C, C++ files, headers, and more.
    """

    def options(self, parser):
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

    def execute(self, config, args):
        groups = args.groups.split(',')
        # join is to have a path separator at the end
        prefix_to_skip = os.path.join(os.path.abspath('.'), '')
        for path in compdb.filelist.list_files(groups, args.path):
            # make descendant paths relative
            if path.startswith(prefix_to_skip):
                path = path[len(prefix_to_skip):]
            print(path)


class CheckDbCommand(RegisteredCommand):
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

    def options(self, parser):
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

    def execute(self, config, args):
        suppressions = []
        for supp in args.suppressions:
            suppressions.extend(
                self._get_suppressions_patterns_from_file(supp))

        databases = []
        for build_dir in args.p:
            cdb = CompilationDatabase.from_directory(build_dir)
            if not cdb:
                sys.stderr.write('error: compilation database not found\n')
                sys.exit(1)
            databases.append(cdb)

        groups = args.groups.split(',')
        db_files = frozenset(
            itertools.chain.from_iterable([cdb.get_all_files()
                                           for cdb in databases]))
        list_files = frozenset(compdb.filelist.list_files(groups, args.path))

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
                columns = struct.unpack('HHHH', fcntl.ioctl(
                    sys.stdout.fileno(), termios.TIOCGWINSZ,
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
    return "\n\n".join(map(lambda s:
                           textwrap.fill(s.strip(), width=paragraph_width),
                           paragraphs))


def main():
    parser = argparse.ArgumentParser(
        description='{}.'.format(__desc__),
        formatter_class=SubcommandHelpFormatter)

    # http://stackoverflow.com/a/18283730/951426
    # http://bugs.python.org/issue9253#msg186387
    subparsers = parser.add_subparsers(
        title='available commands', metavar='<command>', dest='command')
    subparsers.dest = 'command'
    # subcommand seems to be required by default in python 2.7 but not 3.5,
    # forcing it to true limit the differences between the two
    subparsers.required = True

    commands = []
    config_spec = compdb.config.ConfigSpec()
    for command_cls in RegisteredCommand:
        command = command_cls()
        commands.append(command)

        command_description = command.help_short.capitalize()
        if not command_description.endswith('.'):
            command_description += "."

        # Format detail description, line wrap manually so that unlike the
        # default formatter_class used for subparser we can have
        # newlines/paragraphs in the detailed description.
        if hasattr(command, 'help_detail'):
            command_description += "\n\n"
            command_description += textwrap.dedent(command.help_detail)

        command_description = textwrap.dedent("""
        description:
        """) + wrap_paragraphs(command_description, 120)

        subparser = subparsers.add_parser(
            command.name,
            formatter_class=SubcommandHelpFormatter,
            help=command.help_short,
            epilog=command_description)
        if callable(getattr(command, 'options', None)):
            command.options(subparser)
        if callable(getattr(command, 'config_spec', None)):
            section_spec = config_spec.get_section_spec(command_cls.name)
            command.config_spec(section_spec)
        subparser.set_defaults(func=command.execute)

    # if no option is specified we default to "help" so we have something
    # useful to show to the user instead of an error because of missing
    # subcommand
    args = parser.parse_args(sys.argv[1:] or ["help"])
    config = compdb.config.LazyTypedConfig(config_spec)
    args.func(config, args)
