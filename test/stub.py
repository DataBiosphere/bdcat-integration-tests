#!/usr/bin/env python
# coding: utf-8
import io
import json
import logging
import sys
import time
import unittest
import os

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # noqa
sys.path.insert(0, pkg_root)  # noqa

logger = logging.getLogger(__name__)


class TestTrivialCase(unittest.TestCase):
    def test_pass(self):
        self.assertEqual(1, 1)

    # def test_fail(self):
    #     self.assertEqual(1, 2)


if __name__ == "__main__":
    unittest.main()
