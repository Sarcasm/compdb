from __future__ import print_function, unicode_literals, absolute_import

import unittest

from compdb.headerdb import subword_split


class Utils(unittest.TestCase):
    def test_subword_split(self):
        self.assertEqual(["Camel", "Case"], subword_split("CamelCase"))
        self.assertEqual(["camel", "Back"], subword_split("camelBack"))
        self.assertEqual(["String", "Ref"], subword_split("StringRef"))
        self.assertEqual(["Gst", "Buffer"], subword_split("GstBuffer"))
        self.assertEqual(["NS", "String"], subword_split("NSString"))
        self.assertEqual(["ALLCAP"], subword_split("ALLCAP"))
        self.assertEqual(["nocap"], subword_split("nocap"))
        self.assertEqual(["One", "Two", "Three", "Four"],
                         subword_split("OneTwoThreeFour"))
        self.assertEqual(["Foo1", "Bar2"], subword_split("Foo1Bar2"))
        self.assertEqual(["123"], subword_split("123"))
        self.assertEqual(["lowercase", "underscore"],
                         subword_split("lowercase_underscore"))
        self.assertEqual(["Funny", "Case", "dash"],
                         subword_split("FunnyCase-dash"))
        # this one is debatable, we could have empty strings too
        self.assertEqual(["underscore"], subword_split("_underscore_"))
        self.assertEqual(["with", "dot"], subword_split("with.dot"))
        self.assertEqual(["with", "space"], subword_split("with space"))


if __name__ == "__main__":
    unittest.main()
