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
# import logging

import geom.debug
from geom import bezier
from geom import transform2d
from inkscape import inkext
from svg import geomsvg

_ = gettext.gettext
# logger = logging.getLogger(__name__)


class PolySmooth(inkext.InkscapeExtension):
    """An Inkscape extension that smoothes polygons.
    """
    # Command line options
    OPTIONSPEC = (
        inkext.ExtOption('--smoothness', '-s', type='int', default=50,
                         help=_('Smoothness in percent')),
        inkext.ExtOption('--new-layer', type='inkbool', default=False,
                         help=_('Create new layer for output.')),
        inkext.ExtOption('--match-style', type='inkbool', default=True,
                         help=_('Match style of input path.')),
        inkext.ExtOption('--polysmooth-stroke',
                         help=_('CSS stroke color')),
        inkext.ExtOption('--polysmooth-stroke-width',
                         help=_('CSS stroke width')),
    )
    # SVG CSS inline style template
    _styles = {
        'polysmooth':
            'fill:none;stroke-opacity:1.0;stroke-linejoin:round;'
            'stroke-width:${polysmooth_stroke_width};'
            'stroke:${polysmooth_stroke};',
    }
    # Default style template values
    _style_defaults = {
        'polysmooth_stroke_width': '1px',
        'polysmooth_stroke': '#000',
    }
    # Default layer name for smoothed output
    _LAYER_NAME = 'polysmooth'

    def run(self):
        """Main entry point for Inkscape extensions.
        """
        # Set up debug SVG output context.
        geom.debug.set_svg_context(self.debug_svg)

        # Update CSS inline styles from templates and/or options
        self._styles.update(self.svg.styles_from_templates(
            self._styles, self._style_defaults, self.options.__dict__))

        # Get a list of selected SVG shape elements and their transforms
        parent_transform = None
        if not self.options.new_layer:
            # This will prevent the parent layer transform from being applied
            # twice when the original element is replaced by the smoothed one.
            parent_transform = transform2d.IDENTITY_MATRIX
        svg_elements = self.svg.get_shape_elements(
            self.get_elements(), parent_transform=parent_transform)
        if not svg_elements:
            # Nothing selected or document is empty
            return

        # Create a new layer for the SVG output.
        if self.options.new_layer:
            new_layer = self.svg.create_layer(self._LAYER_NAME,
                                              incr_suffix=True)

        default_style = self._styles['polysmooth']
        smoothness = self.options.smoothness / 100.0
        for element, element_transform in svg_elements:
            # Convert the SVG element to Line/Arc/CubicBezier paths
            pathlist = geomsvg.svg_element_to_geometry(
                element, element_transform=element_transform)
            for path in pathlist:
                new_path = bezier.smooth_path(path, smoothness)
                if self.options.new_layer:
                    parent = new_layer
                else:
                    # Replace the original element with the smoothed one
                    parent = element.getparent()
                    parent.remove(element)
                style = default_style
                if self.options.match_style:
                    style = element.get('style')
                path_is_closed = (path[-1].p2 == path[0].p1)
                self.svg.create_polypath(new_path, style=style,
                                         close_path=path_is_closed,
                                         parent=parent)

if __name__ == '__main__':
    PolySmooth().main(PolySmooth.OPTIONSPEC)
