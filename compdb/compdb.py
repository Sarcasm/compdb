from __future__ import print_function, unicode_literals, absolute_import

import argparse
import codecs
import itertools
import json
import os
import pprint
import re
import shlex
import sys
import textwrap

from . import __version__

__prog__ = os.path.splitext(os.path.basename(__file__))[0]


# The issue this function tries to solve is to have a text writer where unicode
# data can be written without decoding error. It should work in the following
# conditions:
# - python 2 & 3, output to terminal
# - python 2 & 3, output to a pipe or shell redirection
#
# When using python 2, if the program output is redirected to a pipe or file,
# the output encoding may be set to 'ascii', potentially producing
# UnicodeEncodeError. Redirections do not seem to cause such issue with python 3
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
# Since we don't want to consume the element the function return a tuple, where
# the first element is a boolean telling whether or not the generator is empty,
# and the second element is a new generator where the first element has been put
# back.
def empty_iterator_wrap(iterator):
    try:
        first = next(iterator)
    except StopIteration:
        return True, None
    return False, itertools.chain([first], iterator)


class CompilationDatabaseRegistry(type):
    def __init__(cls, name, bases, nmspc):
        super(CompilationDatabaseRegistry, cls).__init__(name, bases, nmspc)
        if not hasattr(cls, 'registry'):
            cls.registry = set()
        if len(bases) > 0:  # skip the base class
            cls.registry.add(cls)

    def __iter__(cls):
        return iter(cls.registry)

    def __str__(cls):
        if cls in cls.registry:
            return cls.__name__
        return cls.__name__ + ": " + ", ".join([sc.__name__ for sc in cls])


if sys.version_info[0] < 3:

    class RegisteredCompilationDatabase():
        __metaclass__ = CompilationDatabaseRegistry
else:
    # Probably a bad idea but the syntax is incompatible in python2
    exec(
        'class RegisteredCompilationDatabase(metaclass=CompilationDatabaseRegistry): pass')


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
    def file_abspath(self):
        return os.path.join(self.directory, self.file)


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

    # TODO: return a generator instead?
    def get_compile_commands(self, filepath):
        commands = []
        for elem in self._data:
            if elem['file'] == filepath:
                commands.append(self._dict_to_compile_command(elem))
        return iter(commands)

    def get_all_files(self):
        return map((lambda entry: entry['file']), self._data)

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
    def __init__(cls, name, bases, nmspc):
        super(CommandRegistry, cls).__init__(name, bases, nmspc)
        if not hasattr(cls, 'registry'):
            cls.registry = set()
        if len(bases) > 0:  # skip the base class
            cls.registry.add(cls)

    def __iter__(cls):
        return iter(sorted(cls.registry, key=lambda c: c.name))

    def __str__(cls):
        if cls in cls.registry:
            return cls.__name__
        return cls.__name__ + ": " + ", ".join([sc.__name__ for sc in cls])


if sys.version_info[0] < 3:

    class RegisteredCommand():
        __metaclass__ = CommandRegistry
else:
    # Probably a bad idea but the syntax is incompatible in python2
    exec('class RegisteredCommand(metaclass=CommandRegistry): pass')


class HelpCommand(RegisteredCommand):
    name = 'help'
    help_short = 'display this help'

    def execute(self, args):
        print("Available commands:")
        command_max_len = max(map(len, [c.name for c in RegisteredCommand]))
        for c in RegisteredCommand:
            print("    {c.name:<{max_len}}   {c.help_short}".format(
                c=c,
                max_len=command_max_len))


class VersionCommand(RegisteredCommand):
    name = 'version'
    help_short = 'display this version of {}'.format(__prog__)

    def options(self, parser):
        parser.add_argument('--short',
                            action='store_true',
                            help='machine readable version')

    def execute(self, args):
        if args.short:
            print(__version__)
        else:
            print(__prog__, "version", __version__)


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
        parser.add_argument('-p',
                            metavar="BUILD-DIR",
                            help='build path(s)',
                            action='append',
                            required=True)

    def execute(self, args):
        cdbs = []
        for build_dir in args.p:
            cdb = CompilationDatabase.from_directory(build_dir)
            if not cdb:
                sys.stderr.write('error: compilation database not found\n')
                sys.exit(1)
            cdbs.append(cdb)
        compile_commands_to_json(
            itertools.chain.from_iterable([cdb.get_all_compile_commands(
            ) for cdb in cdbs]), get_utf8_writer())


class FindCommand(RegisteredCommand):
    name = 'find'
    help_short = 'find compile command(s) for a file'
    help_detail = 'Exit with status 1 if no compile command is found.'

    def options(self, parser):
        parser.add_argument('-p',
                            metavar="BUILD-DIR",
                            help='build path',
                            required=True)
        parser.add_argument(
            'file',
            help="file to search for in the compilation database")

    def execute(self, args):
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
    file_norm = os.path.normpath(compile_command.file_abspath)
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
            arg_norm = os.path.normpath(os.path.join(compile_command.directory,
                                                     command[i]))
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
    return new


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
    return os.path.dirname(os.path.join(compile_command.directory,
                                        compile_command.file))


SUBWORD_SEPARATORS_RE = re.compile("[^A-Za-z0-9]")

# The comment is shitty because I don't fully understand what is going.
# Shamelessly stolen, then modified from:
# - http://stackoverflow.com/a/29920015/951426
SUBWORD_CAMEL_SPLIT_RE = re.compile(r"""
.+?                             # capture text instead of discarding (#1)
(
  (?:(?<=[a-z0-9]))             # non-capturing positive lookbehind assertion
  (?=[A-Z])                     # match first uppercase letter without consuming
|
  (?<=[A-Z])                    # an upper char should prefix
  (?=[A-Z][a-z0-9])             # an upper char, lookahead assertion: does not
                                # consume the char
|
$                               # ignore capture text #1
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
        src_file = os.path.normpath(compile_command.file_abspath)
        for quote, filename in get_file_includes(src_file):
            header_abspath = None
            score = 0
            if quote == '"':
                candidate = os.path.normpath(os.path.join(implicit_search_path,
                                                          filename))
                if os.path.isfile(candidate):
                    header_abspath = candidate
            if not header_abspath:
                for search_path in header_search_paths:
                    candidate = os.path.normpath(os.path.join(search_path,
                                                              filename))
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
        db_update = make_headerdb1(
            (cmd for _, cmd in db_update.values()), headerdb)
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
        parser.add_argument('-p',
                            metavar="BUILD-DIR",
                            help='build path',
                            required=True)

    def execute(self, args):
        build_dir = args.p
        cdb = CompilationDatabase.from_directory(build_dir)
        if not cdb:
            sys.stderr.write('error: compilation database not found\n')
            sys.exit(1)
        header_db = make_headerdb(cdb.get_all_compile_commands(),
                                  get_utf8_writer())


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
                import fcntl, termios, struct
                columns = struct.unpack('HHHH', fcntl.ioctl(
                    sys.stdout.fileno(), termios.TIOCGWINSZ,
                    struct.pack('HHHH', 0, 0, 0, 0)))[1]
            except (ImportError, IOError):
                pass
    return columns


def wrap_paragraphs(text):
    paragraph_width = term_columns()
    if paragraph_width > 2:
        paragraph_width -= 2
    paragraphs = text.split('\n\n')
    return "\n\n".join(map(lambda s: textwrap.fill(s.strip(), width=paragraph_width), paragraphs))


class App:
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description='A compilation database helper tool.',
            formatter_class=SubcommandHelpFormatter)

        # http://stackoverflow.com/a/18283730/951426
        # http://bugs.python.org/issue9253#msg186387
        subparsers = self.parser.add_subparsers(title='Available commands',
                                                metavar='<command>',
                                                dest='command')
        subparsers.dest = 'command'
        # subcommand seems to be required by default in python 2.7 but not 3.5,
        # forcing it to true limit the differences between the two
        subparsers.required = True

        commands = []
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
            """) + wrap_paragraphs(command_description)

            parser = subparsers.add_parser(
                command.name,
                formatter_class=argparse.RawDescriptionHelpFormatter,
                help=command.help_short,
                epilog=command_description)
            if callable(getattr(command_cls, 'options', None)):
                command.options(parser)
            parser.set_defaults(func=command.execute)

    def run(self):
        # if no option is specified we default to "help" so we have something
        # useful to show to the user instead of an error because of missing
        # subcommand
        args = self.parser.parse_args(sys.argv[1:] or ["help"])
        args.func(args)
