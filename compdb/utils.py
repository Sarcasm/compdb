from __future__ import print_function, unicode_literals, absolute_import

import itertools
import os


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


def get_friendly_path(path):
    full_path = os.path.normpath(path)
    rel_path = os.path.relpath(full_path)
    if rel_path.startswith(os.path.join(os.pardir, os.pardir)):
        friendly_path = full_path
    else:
        friendly_path = rel_path
    return friendly_path
