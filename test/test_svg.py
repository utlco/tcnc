#!/usr/bin/env python

"""Test the svg module
"""

import os
import filecmp
import unittest

if __name__ == '__main__':
    import sys
    sys.path.append('../tcnc')

from svg import svg
from svg import css

_TEST_INPUT_FILE = 'svg/test_output_cmp.svg'
_TEST_OUTPUT_FILE = 'svg/test_output.svg'
_TEST_OUTPUT_COMPARE_FILE = 'svg/test_output_cmp.svg'

class TestSVGMethods(unittest.TestCase):
    """
    Test various parts of the svg package...
    """
    CSS_TEST_COLORS_RED = ['red', '#ff0000', '#FF0000', '#f00',
                           'rgb(255, 0, 0), rgba(255, 0, 0, 100%)',
                           'rgb (100%, 0, 0)',
                           'ff0000', 'f00']
    CSS_TEST_COLORS_BAD = ['browntrout', '#FX00ca', '#ff', 'rgb(x)']

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_parsewrite(self):
        # Test parsing and writing
        self.svg = svg.SVGContext.parse(_TEST_INPUT_FILE)
        self.svg.write(_TEST_OUTPUT_FILE)
        self.assertTrue(filecmp.cmp(_TEST_OUTPUT_COMPARE_FILE,
                                    _TEST_OUTPUT_FILE))
        os.remove(_TEST_OUTPUT_FILE)

    def test_css(self):
        for css_color in self.CSS_TEST_COLORS_RED:
            rgb = css.csscolor_to_rgb(css_color)
            self.assertTrue(len(rgb) == 3 or len(rgb) == 4)
            self.assertTrue(rgb[0] == 255 and rgb[1] == 0 and rgb[2] == 0)

        for css_color in self.CSS_TEST_COLORS_BAD:
            rgb = css.csscolor_to_rgb(css_color)
            self.assertTrue(rgb[0] == 0 and rgb[1] == 0 and rgb[2] == 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)