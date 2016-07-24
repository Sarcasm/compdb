#!/usr/bin/env python

from __future__ import print_function, unicode_literals

import argparse
import fnmatch
import io
import json
import os
import sys


def get_suppressions_patterns_from_file(path):
    patterns = []
    with io.open(path, 'r', encoding='utf-8') as f:
        for line in f:
            pattern = line.partition('#')[0].rstrip()
            if pattern:
                patterns.append(pattern)
    return patterns


def print_set_summary(files, name):
    print("Only in {}:".format(name))
    cwd = os.getcwd()
    for path in sorted(files):
        if path.startswith(cwd):
            pretty_filename = os.path.relpath(path)
        else:
            pretty_filename = path
        print('  {}'.format(pretty_filename))


def main():
    parser = argparse.ArgumentParser(
        description='Verify headerdb contains specified files.')
    parser.add_argument('headerdb', help='A header compilation database')
    parser.add_argument('filelist', help='List of file to check against')
    parser.add_argument('--suppressions',
                        action='append',
                        default=[],
                        help='Add suppression file')

    args = parser.parse_args()

    with open(args.headerdb) as f:
        db_files = [
            os.path.normpath(os.path.join(entry['directory'], entry['file']))
            for entry in json.load(f)
        ]

    with open(args.filelist) as f:
        list_files = [os.path.abspath(line.rstrip('\n')) for line in f]

    suppressions = []
    for supp in args.suppressions:
        suppressions.extend(get_suppressions_patterns_from_file(supp))

    db_files = frozenset(db_files)
    list_files = frozenset(list_files)

    # this only is not a hard error, files may be in system paths or build
    # directory for example
    db_only = db_files - list_files
    if db_only:
        print_set_summary(db_only, args.headerdb)

    list_only = list_files - db_files
    # filter out suppressions
    # could convert the fnmatch expression to mutex and use re.search()
    # instead of prefixing */ pattern
    suppressions = ['*/{}'.format(supp) for supp in suppressions]
    for supp in suppressions:
        filterred = set(fnmatch.filter(list_only, supp))
        list_only -= filterred

    if not list_only:
        sys.exit(0)

    # print difference an exit with error
    print_set_summary(list_only, args.filelist)
    print("error: some files are missing from the header databases",
          file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    main()
