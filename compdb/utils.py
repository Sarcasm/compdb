from __future__ import print_function, unicode_literals, absolute_import

import codecs
import contextlib
import itertools
import os
import re
import sys

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


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


# compatibility function,
# not as smart as the version of the Python standard library
@contextlib.contextmanager
def suppress(*exceptions):
    """Context manager to suppress specified exceptions
         with suppress(OSError):
             os.remove(somefile)
    """
    try:
        yield
    except exceptions:
        pass


def re_fullmatch(regex, string, flags=0):
    """Emulate python-3.4 re.fullmatch()."""
    return re.match("(?:" + regex + r")\Z", string, flags=flags)


# The issue this function tries to solve is to have a text writer where unicode
# data can be written without decoding error. It should work in the following
# conditions:
# - python 2 & 3, output to terminal
# - python 2 & 3, output to a pipe or shell redirection
# - python 2 & 3, output to a StringIO
#
# When using python 2, if the program output is redirected to a pipe or file,
# the output encoding may be set to 'ascii',
# potentially producing UnicodeEncodeError.
# Redirections do not seem to cause such issue with python 3
# but explicit utf-8 encoding seems a sensible choice to output data to be
# consumed by other programs (e.g: JSON).
def stdout_unicode_writer():
    stream = sys.stdout
    if isinstance(stream, StringIO):
        return stream
    if hasattr(stream, 'buffer'):
        stream = stream.buffer
    return codecs.getwriter('utf-8')(stream)


def get_friendly_path(path):
    full_path = os.path.normpath(path)
    rel_path = os.path.relpath(full_path)
    if rel_path.startswith(os.path.join(os.pardir, os.pardir)):
        friendly_path = full_path
    else:
        friendly_path = rel_path
    return friendly_path


def logical_abspath(p):
    """Same as os.path.abspath,
    but use the logical current working to expand relative paths.
    """
    if os.path.isabs(p):
        return os.path.normpath(p)
    cwd = os.getenv('PWD')
    if cwd and os.path.isabs(cwd) and os.path.samefile(cwd, '.'):
        return os.path.normpath(os.path.join(cwd, p))
    return os.path.abspath(p)


def locate_dominating_file(name, start_dir=os.curdir):
    curdir = os.path.abspath(start_dir)
    olddir = None
    while not curdir == olddir:
        if os.path.exists(os.path.join(curdir, name)):
            return curdir
        olddir = curdir
        curdir = os.path.dirname(curdir)
    return None
