#!/usr/bin/env python

from __future__ import print_function, unicode_literals, absolute_import

import unittest

from context import compdb


class Utils(unittest.TestCase):
    def test_subword_split(self):
        self.assertEqual(["Camel", "Case"], compdb.subword_split("CamelCase"))
        self.assertEqual(["camel", "Back"], compdb.subword_split("camelBack"))
        self.assertEqual(["String", "Ref"], compdb.subword_split("StringRef"))
        self.assertEqual(["Gst", "Buffer"], compdb.subword_split("GstBuffer"))
        self.assertEqual(["NS", "String"], compdb.subword_split("NSString"))
        self.assertEqual(["ALLCAP"], compdb.subword_split("ALLCAP"))
        self.assertEqual(["nocap"], compdb.subword_split("nocap"))
        self.assertEqual(["One", "Two", "Three", "Four"],
                         compdb.subword_split("OneTwoThreeFour"))
        self.assertEqual(["Foo1", "Bar2"], compdb.subword_split("Foo1Bar2"))
        self.assertEqual(["123"], compdb.subword_split("123"))
        self.assertEqual(["lowercase", "underscore"],
                         compdb.subword_split("lowercase_underscore"))
        self.assertEqual(["Funny", "Case", "dash"],
                         compdb.subword_split("FunnyCase-dash"))
        # this one is debatable, we could have empty strings too
        self.assertEqual(["underscore"], compdb.subword_split("_underscore_"))
        self.assertEqual(["with", "dot"], compdb.subword_split("with.dot"))
        self.assertEqual(["with", "space"], compdb.subword_split("with space"))

if __name__ == "__main__":
    unittest.main()
