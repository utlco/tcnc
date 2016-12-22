#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright 2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
An Inkscape extension that blablaba.

====
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division, unicode_literals)
from future_builtins import *

import gettext
# import logging

import geom.debug
from svg import geomsvg
from inkscape import inkext

__version__ = "0.1"

_ = gettext.gettext
# logger = logging.getLogger(__name__)


class MyExtension(inkext.InkscapeExtension):
    """Inkscape extension barebones template.
    """
    OPTIONSPEC = (
        inkext.ExtOption('--option-name1', type='docunits', default=1.0,
                         help=_('Document unit option description')),
        inkext.ExtOption('--option-name2', type='inkbool', default=True,
                         help=_('Boolean option description')),
        inkext.ExtOption('--option-name3', type='int', default=1,
                         help=_('Integer option description')),
    )

    def run(self):
        """Main entry point for Inkscape extension.
        """
        # Initialize the debug SVG context for the geometry package
        geom.debug.set_svg_context(self.debug_svg)

        # Get a list of selected SVG shape elements and their transforms
        svg_elements = self.svg.get_shape_elements(self.get_elements())
        if svg_elements:
            path_list = geomsvg.svg_to_geometry(svg_elements)
        else:
            # Nothing selected or document is empty
            path_list = ()



if __name__ == '__main__':
    MyExtension().main(optionspec=MyExtension.OPTIONSPEC)
