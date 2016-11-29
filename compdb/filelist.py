from __future__ import print_function, unicode_literals, absolute_import

import os


def list_files(groups, paths):
    source_exts = [
        '.c',
        '.C',
        '.cc',
        '.c++',
        '.C++',
        '.cxx',
        '.cpp',
    ]
    header_exts = [
        '.h',
        '.H',
        '.hh',
        '.h++',
        '.H++',
        '.hxx',
        '.hpp',
    ]

    extensions = []
    if 'source' in groups:
        extensions += source_exts
    if 'header' in groups:
        extensions += header_exts
    for path in paths:
        for root, dirnames, filenames in os.walk(os.path.abspath(path)):
            for filename in filenames:
                if os.path.splitext(filename)[1] in extensions:
                    yield os.path.join(root, filename)
