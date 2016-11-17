from __future__ import print_function, unicode_literals, absolute_import

import os
import sys

# allow invokation of the style 'python /path/to/compdb'
if __package__ == '':
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from compdb import main

if __name__ == '__main__':
    sys.exit(main())
