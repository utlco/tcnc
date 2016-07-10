#!/usr/bin/env python
#
# This will install the packages for standalone
# command-line usage. To install as Inkscape
# extensions please read the instructions in README.md

from distutils.core import setup

setup(name='tcnc',
      version='0.2',
      description='TCNC Inkscape extensions and geometry libraries.',
      author='Claude Zervas',
      author_email='claude@utlco.com',
      package_dir={'': '.',},
      packages=['tcnc',],
      requires=['lxml',],
      )