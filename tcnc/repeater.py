#!/usr/bin/env python
#-----------------------------------------------------------------------------#
#    Copyright 2012-2016 Claude Zervas
#    email: claude@utlco.com
#-----------------------------------------------------------------------------#
"""Smooth non-G1 path nodes using Bezier curves and draw it as SVG.

Works for polyline/polygons made of line/arc segments.

This can be invoked as an Inkscape extension or from the command line.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division, unicode_literals)
# from future_builtins import (ascii, filter, hex, map, oct, zip)

import gettext
import logging
from copy import deepcopy

from lxml import etree

import geom.debug
from geom import transform2d
from geom import polygon
from inkscape import inkext
from svg import svg

_ = gettext.gettext
logger = logging.getLogger(__name__)


class Repeater(inkext.InkscapeExtension):
    """An Inkscape extension that duplicates paths along a straight line.
    """
    # Command line options
    OPTIONSPEC = (
        inkext.ExtOption('--copies', type='int', default=1,
                         help=_('Number of copies')),
        inkext.ExtOption('--interval', type='docunits', default=1.0,
                         help=_('Repeat interval')),
        inkext.ExtOption('--angle', type='degrees', default=0.0,
                         help=_('Angle from horizontal')),
        inkext.ExtOption('--new-layer', type='inkbool', default=False,
                         help=_('Create new layer for output.')),
    )
    # Default layer name for output
    _LAYER_NAME = 'repeater'

    def run(self):
        """Main entry point for Inkscape extensions.
        """
        # Set up debug SVG output context.
        geom.debug.set_svg_context(self.debug_svg)

        selected_elements = self.get_elements()
        if not len(selected_elements):
            # Nothing selected or document is empty
            return

        # Create a new layer for the SVG output.
        layer = None
        if self.options.new_layer:
            layer = self.svg.create_layer(self._LAYER_NAME,
                                              incr_suffix=True)

        for n in range(self.options.copies):
            for element in selected_elements:
                m_elem = self.svg.parse_transform_attr(element.get('transform'))
                v = geom.P.from_polar(self.options.interval * (n + 1),
                                      - self.options.angle)
                m_translate = transform2d.matrix_translate(v.x, v.y)
                m_transform = transform2d.compose_transform(m_elem, m_translate)
                transform_attr = svg.transform_attr(m_transform)
                elem_copy = deepcopy(element)
                elem_copy.set('transform', transform_attr)
#                elem_copy.set('id', element.get('id') + '_r')
                self.svg.add_elem(elem_copy, parent=layer)

if __name__ == '__main__':
    Repeater().main(Repeater.OPTIONSPEC)
