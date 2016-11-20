from __future__ import print_function, unicode_literals, absolute_import


from compdb.__about__ import __version__
from compdb.compdb import App

__all__ = ["__version__"]


def main():
    app = App()
    app.run()
