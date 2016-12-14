from __future__ import print_function, unicode_literals, absolute_import

import os
import sys

# allow invokation of the style 'python /path/to/compdb'
if __package__ == '':
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from compdb.cli import main  # noqa: E402

if __name__ == '__main__':
    sys.exit(main())
