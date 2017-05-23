from __future__ import print_function, unicode_literals, absolute_import

import unittest

from compdb.models import CompileCommand


class CompileCommandTest(unittest.TestCase):
    def test_comparable(self):
        a1 = CompileCommand("/", "a.c", ["cc"])
        a2 = CompileCommand("/", "a.c", ["cc"])
        b = CompileCommand("/", "b.c", ["cc"])
        self.assertTrue(a1 == a2)
        self.assertFalse(a1 == b)
        self.assertTrue(a1 != b)
        self.assertFalse(a1 != a2)
        self.assertEqual(a1, a2)


if __name__ == "__main__":
    unittest.main()
