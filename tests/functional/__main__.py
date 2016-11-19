from __future__ import print_function, unicode_literals, absolute_import

import os
import unittest

# alternatively: one can use the command line like this:
#       python -m unittest discover '--pattern=*.py'
if __name__ == '__main__':
    local_path = os.path.abspath(os.path.dirname(__file__))
    top_level = os.path.dirname(os.path.dirname(local_path))
    testsuite = unittest.TestLoader().discover(
        local_path, top_level_dir=top_level, pattern="test_*.py")
    unittest.TextTestRunner(verbosity=1).run(testsuite)
