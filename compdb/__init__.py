from __future__ import print_function, unicode_literals, absolute_import

from compdb.__about__ import (
    __author__,
    __url__,
    __desc__,
    __prog__,
    __version__,
)

__all__ = [
    '__author__',
    '__desc__',
    '__prog__',
    '__url__',
    '__version__',
]


class CompdbError(Exception):
    '''Base exception for errors raised by compdb'''

    def __init__(self, message, cause=None):
        super(CompdbError, self).__init__(message)
        self.cause = cause


class NotImplementedError(NotImplementedError, CompdbError):
    pass
