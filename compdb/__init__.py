from __future__ import print_function, unicode_literals, absolute_import

# The version as used in the setup.py
__version__ = '0.0.1'

from compdb.compdb import App


def main():
    app = App()
    app.run()


if __name__ == '__main__':
    sys.exit(main())
