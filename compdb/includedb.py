from __future__ import print_function, unicode_literals, absolute_import

import logging
import os
import re

from collections import deque

import compdb.complementer.headerdb
import compdb.utils

from compdb.models import CompilationDatabaseInterface

try:
    FileNotFoundError
except NameError:
    # py2
    FileNotFoundError = IOError

logger = logging.getLogger(__name__)


class IncludeDirective(object):
    __slots__ = [
        'header_name', 'is_angled', 'search_path', 'source_file',
        'source_is_main_file'
    ]

    def __init__(self, header_name, is_angled, search_path, source_file,
                 source_is_main_file):
        self.header_name = header_name
        self.is_angled = is_angled
        self.search_path = search_path
        self.source_file = source_file
        self.source_is_main_file = source_is_main_file


class Preprocessor(object):
    def __init__(self):
        self.callbacks = []
        self._processed = set()

    def register_include_callback(self, cb):
        self.callbacks.append(cb)

    def preprocess(self, compile_command):
        search_paths = compdb.complementer.headerdb.extract_include_dirs(
            compile_command)
        includer_stack = [compile_command.normfile]
        if includer_stack[0] in self._processed:
            return

        self._processed.add(includer_stack[0])
        iter_stack = [self._iter_includes(includer_stack[0])]

        while iter_stack:
            try:
                quote, header_name = next(iter_stack[-1])
            except StopIteration:
                iter_stack.pop()
                includer_stack.pop()
                continue

            includer = includer_stack[-1]
            is_angled = quote == "<"
            search_path = self._resolve_search_path(header_name, is_angled,
                                                    search_paths, includer)

            if not search_path:
                if is_angled:
                    logger.debug("%s: could not resolve header: <%s>",
                                 compdb.utils.get_friendly_path(includer),
                                 header_name)
                else:
                    logger.warning("%s: could not resolve header: \"%s\"",
                                   compdb.utils.get_friendly_path(includer),
                                   header_name)
                continue

            logger.debug("%s: resolved header: %s%s%s",
                         compdb.utils.get_friendly_path(includer), quote,
                         header_name, is_angled and '>' or '"')

            if self.callbacks:
                source_is_main_file = len(includer_stack) == 1
                include_directive = IncludeDirective(header_name, is_angled,
                                                     search_path, includer,
                                                     source_is_main_file)
                for cb in self.callbacks:
                    cb(include_directive)

            includee = os.path.normpath(os.path.join(search_path, header_name))
            if includee in self._processed:
                continue
            self._processed.add(includee)
            includer_stack.append(includee)
            iter_stack.append(self._iter_includes(includer_stack[-1]))

    def _iter_includes(self, path):
        try:
            with open(path, "rb") as istream:
                include_pattern = re.compile(
                    br'\s*#\s*include\s+(?P<quote>["<])(?P<filename>.+?)[">]')
                for b_line in istream:
                    b_match = re.match(include_pattern, b_line)
                    if not b_match:
                        continue
                    u_quote = b_match.group('quote').decode('ascii')
                    b_filename = b_match.group('filename')
                    try:
                        u_filename = b_filename.decode('utf-8')
                    except UnicodeDecodeError:
                        u_filename = b_filename.decode('latin-1')
                    yield (u_quote, u_filename)
        except FileNotFoundError as exc:
            # tolerate, but log, missing files [GH-4]
            logger.warning("%s", exc)

    def _iter_search_paths(self, is_angled, search_paths, includer):
        if not is_angled:
            yield os.path.dirname(includer)
        for search_path in search_paths:
            yield search_path

    def _resolve_search_path(self, header_name, is_angled, search_paths,
                             includer):
        for search_path in self._iter_search_paths(is_angled, search_paths,
                                                   includer):
            if os.path.isfile(os.path.join(search_path, header_name)):
                return search_path


class IncludedByDatabase(CompilationDatabaseInterface):
    """Represent included-by relationship of headers

A graph represented implemented as an adjacent list.

See also https://www.python.org/doc/essays/graphs/
"""

    def __init__(self, graph, database):
        self.graph = graph
        self.database = database
        self.__db_index = None

    def __repr__(self):
        return '<IncludedByGraph: graph = {}, database = {}>'.format(
            self.graph, self.database)

    def __str__(self):
        return self.__repr__()

    # first iterate over direct includer, then 2nd degree includers, ...
    # Precondition: path is in the tree
    def _bfs_walk_from(self, path):
        to_visit = deque((path, ))
        visited = {path}
        depth_checkpoint = path
        depth = 0
        while True:
            try:
                node = to_visit.popleft()
            except IndexError:
                return

            if node == depth_checkpoint:
                depth_checkpoint = None
                depth += 1

            for adjacent_node in self.graph.get(node, []):
                if adjacent_node in visited:
                    continue
                yield adjacent_node, depth
                visited.add(adjacent_node)
                to_visit.append(adjacent_node)
                if not depth_checkpoint:
                    depth_checkpoint = adjacent_node

    @property
    def _db_index(self):
        if self.__db_index is None:
            self.__db_index = frozenset(self.database.get_all_files())
        return self.__db_index

    def _find_best(self, path):
        best = None
        best_score = None
        last_depth = 0
        for includer, depth in self._bfs_walk_from(path):
            if depth != last_depth and best:
                # we don't want to go too far down in the include tree,
                # the best file is one with the shortest depth,
                # often a direct includer (depth 1)
                break
            if includer not in self._db_index:
                # this includer is also an include, skip it
                continue
            score = compdb.complementer.headerdb.score_other_file(
                path, includer)
            if best_score is None or score > best_score:
                best_score = score
                best = includer
        return best

    def get_compile_commands(self, path):
        best = self._find_best(path)
        if best:
            for compile_command in self.database.get_compile_commands(best):
                yield compdb.complementer.headerdb.derive_compile_command(
                    path, compile_command)
                # stop after one compile command
                break

    def get_all_files(self):
        return iter(self.graph.keys())

    def all_files_unique(self):
        return True

    def get_all_compile_commands(self):
        for file in self.get_all_files():
            for compile_command in self.get_compile_commands(file):
                yield compile_command


class IncludedByGraphFiller(object):
    def __init__(self, included_by_graph, database):
        self.included_by_graph = included_by_graph
        self.database = database
        self.db_files = None

    def include_callback(self, include_directive):
        includee = os.path.normpath(
            os.path.join(include_directive.search_path,
                         include_directive.header_name))
        if includee == include_directive.source_file:
            # self include are technically possible,
            # however, we don't want to store them for now
            return
        if self.db_files is None:
            self.db_files = set(self.database.get_all_files())
        if includee in self.db_files:
            # don't store files which are in the database
            return
        # is this useful information at this point?
        # has_compile_command = False
        # if include_directive.source_is_main_file or \
        #    include_directive.source_file in self.db_files:
        #     has_compile_command = True
        self.add(includee, include_directive.source_file)

    def add(self, includee, includer):
        try:
            lst = self.included_by_graph[includee]
            if includer not in lst:
                lst.append(includer)
        except KeyError:
            self.included_by_graph[includee] = [includer]


class IncludeIndexBuilder(object):
    # return included-by relationship of headers
    def build(self, database):
        # Represent included-by relationship of headers
        #
        # The graph is a dict representing an adjacency list
        included_by_graph = {}
        pp = Preprocessor()
        filler = IncludedByGraphFiller(included_by_graph, database)
        pp.register_include_callback(filler.include_callback)
        for compile_command in database.get_all_compile_commands():
            pp.preprocess(compile_command)
        return IncludedByDatabase(included_by_graph, database)
