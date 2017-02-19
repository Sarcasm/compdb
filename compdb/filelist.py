from __future__ import print_function, unicode_literals, absolute_import

import fnmatch
import itertools
import os


class FileScanner(object):
    def __init__(self):
        self.extensions = []
        self.suppressions = []
        self.source_exts = [
            '.c',
            '.C',
            '.cc',
            '.c++',
            '.C++',
            '.cxx',
            '.cpp',
        ]
        self.header_exts = [
            '.h',
            '.H',
            '.hh',
            '.h++',
            '.H++',
            '.hxx',
            '.hpp',
        ]

    def enable_group(self, group):
        if group == 'source':
            self.extensions += self.source_exts
        elif group == 'header':
            self.extensions += self.header_exts

    def add_suppressions(self, suppressions):
        # filter out suppressions
        # could convert the fnmatch expression to regex
        # and use re.search() instead of prefixing */ pattern
        self.suppressions.extend(
            ['*/{}'.format(supp) for supp in suppressions])

    def _accept_path(self, path):
        if os.path.splitext(path)[1] not in self.extensions:
            return False
        for suppression in self.suppressions:
            if fnmatch.fnmatchcase(path, suppression):
                return False
        return True

    def scan(self, path):
        for root, dirnames, filenames in os.walk(os.path.abspath(path)):
            for filename in filenames:
                out_path = os.path.join(root, filename)
                if self._accept_path(out_path):
                    yield out_path

    def scan_many(self, paths):
        return itertools.chain.from_iterable((self.scan(path)
                                              for path in paths))
