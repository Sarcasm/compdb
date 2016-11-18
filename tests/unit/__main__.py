#!/usr/bin/env python

import os
import unittest

LOCAL_PATH = os.path.abspath(os.path.dirname(__file__))

# alternatively: one can use the command line like this:
#       python -m unittest discover '--pattern=*.py'
if __name__ == '__main__':
    testsuite = unittest.TestLoader().discover(LOCAL_PATH, pattern="test_*.py")
    unittest.TextTestRunner(verbosity=1).run(testsuite)
