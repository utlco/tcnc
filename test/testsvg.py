#!/usr/bin/env python

"""Test the svg module
"""

import os
import filecmp
import unittest

if __name__ == '__main__':
    import sys
    sys.path.append('../tcnc')

from lib import svg

_TEST_INPUT_FILE = 'svg/test_output_cmp.svg'
_TEST_OUTPUT_FILE = 'svg/test_output.svg'
_TEST_OUTPUT_COMPARE_FILE = 'svg/test_output_cmp.svg'

class TestSVGMethods(unittest.TestCase):

    def setUp(self):
        self.svg = svg.SVGContext.parse(_TEST_INPUT_FILE)

    def tearDown(self):
        os.remove(_TEST_OUTPUT_FILE)

    def test_parsewrite(self):
        # Test parsing and writing
        self.svg.write(_TEST_OUTPUT_FILE)
        self.assertTrue(filecmp.cmp(_TEST_OUTPUT_COMPARE_FILE,
                                    _TEST_OUTPUT_FILE))


if __name__ == '__main__':
    unittest.main(verbosity=2)