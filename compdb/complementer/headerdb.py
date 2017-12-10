from __future__ import print_function, unicode_literals, absolute_import

import os
import re

from compdb.backend.memory import InMemoryCompilationDatabase
from compdb.complementer import ComplementerInterface
from compdb.models import CompileCommand


def sanitize_compile_options(compile_command):
    filename = os.path.splitext(compile_command.file)[1]
    file_norm = compile_command.normfile
    adjusted = []
    i = 0
    arguments = compile_command.arguments
    while i < len(arguments):
        # end of options, skip all positional arguments (source files)
        if arguments[i] == "--":
            break
        # strip -c
        if arguments[i] == "-c":
            i += 1
            continue
        # strip -o <output-file> and -o<output-file>
        if arguments[i].startswith("-o"):
            if arguments[i] == "-o":
                i += 2
            else:
                i += 1
            continue
        # skip input file
        if arguments[i].endswith(filename):
            arg_norm = os.path.normpath(
                os.path.join(compile_command.directory, arguments[i]))
            if file_norm == arg_norm:
                i += 1
                continue
        adjusted.append(arguments[i])
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
    header_file_relative = mimic_path_relativity(header_file, reference.file,
                                                 reference.directory)
    args = sanitize_compile_options(reference)
    args.extend(["-c", header_file_relative])
    return CompileCommand(
        directory=reference.directory,
        file=header_file_relative,
        arguments=args)


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
    arguments = sanitize_compile_options(compile_command)
    while i < len(arguments):
        # -I <dir> and -I<dir>
        if arguments[i].startswith("-I"):
            if arguments[i] == "-I":
                i += 1
                header_search_path.append(arguments[i])
            else:
                header_search_path.append(arguments[i][2:])
        i += 1
    return [
        os.path.join(compile_command.directory, p) for p in header_search_path
    ]


def get_implicit_header_search_path(compile_command):
    return os.path.dirname(
        os.path.join(compile_command.directory, compile_command.file))


SUBWORD_SEPARATORS_RE = re.compile("[^A-Za-z0-9]")

# The comment is shitty because I don't fully understand what is going on.
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
    Note that the score can be a negative value.
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


class _Data(object):
    __slots__ = ['score', 'compile_command', 'db_idx']

    def __init__(self, score=0, compile_command=None, db_idx=-1):
        self.score = score
        if compile_command is None:
            self.compile_command = {}
        else:
            self.compile_command = compile_command
        self.db_idx = db_idx


def _make_headerdb1(compile_commands_iter, db_files, db_idx, header_mapping):
    for compile_command in compile_commands_iter:
        implicit_search_path = get_implicit_header_search_path(compile_command)
        header_search_paths = extract_include_dirs(compile_command)
        src_file = compile_command.normfile
        for quote, filename in get_file_includes(src_file):
            header_abspath = None
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
            # skip files already present in the database
            if norm_abspath in db_files:
                continue
            score = score_other_file(src_file, norm_abspath)
            try:
                data = header_mapping[norm_abspath]
            except KeyError:
                data = _Data(score=(score - 1))
                header_mapping[norm_abspath] = data
            if score > data.score:
                data.score = score
                data.compile_command = derive_compile_command(
                    norm_abspath, compile_command)
                data.db_idx = db_idx


def make_headerdb(layers):
    databases_len = len(layers[0])
    complementary_databases = [
        InMemoryCompilationDatabase() for _ in range(databases_len)
    ]

    db_files = set()
    for layer in layers:
        for database in layer:
            db_files.update(database.get_all_files())

    # loop until there is nothing more to resolve
    # we first get the files directly included by the compilation database
    # then the files directly included by these files and so on
    while True:
        # mapping of <header normalized absolute path> -> _Data
        db_update = {}
        for layer in layers:
            for db_idx, database in enumerate(layer):
                _make_headerdb1(database.get_all_compile_commands(), db_files,
                                db_idx, db_update)
        if not db_update:
            break
        layers = [[
            InMemoryCompilationDatabase() for _ in range(databases_len)
        ]]
        for k, v in db_update.items():
            db_files.add(k)
            for db_list in (layers[0], complementary_databases):
                db_list[v.db_idx].compile_commands.append(v.compile_command)
    return complementary_databases


class Complementer(ComplementerInterface):
    def complement(self, layers):
        return make_headerdb(layers)
