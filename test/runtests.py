#!/usr/bin/env python

"""
Run the entire test suite.
"""
import sys
import unittest

# Add the target package to PYTHONPATH.
# This needs to be done before importing the unit test modules
# since they in turn import modules from the target package.
sys.path.append('../tcnc')

import svgtest

# suite = unittest.TestLoader().loadTestsFromTestCase(svgtest.TestSVGMethods)
suite = unittest.TestLoader().discover('.')
unittest.TextTestRunner(verbosity=2).run(suite)


