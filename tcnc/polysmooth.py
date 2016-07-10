#!/usr/bin/env python
#-----------------------------------------------------------------------------#
#    Copyright 2012-2016 Claude Zervas
#    email: claude@utlco.com
#-----------------------------------------------------------------------------#
"""Smooth non-G1 path nodes using Bezier curves and draw it as SVG.

This can be invoked as an Inkscape extension or from the command line.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import gettext
import logging

from lib import inkext
from lib import geomsvg
from lib import geom

from lib.geom import bezier

_ = gettext.gettext
logger = logging.getLogger(__name__)


class PolySmooth(inkext.InkscapeExtension):
    """An Inkscape extension that smoothes polygons.
    """
    # Command line options
    _OPTIONSPEC = (
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
    _LAYER_NAME = 'polysmooth'

    def run(self):
        """Main entry point for Inkscape extensions.
        """
        # Set up debug SVG output context.
        geom.debug.set_svg_context(self.debug_svg)

        # Update CSS inline styles from templates
        self._styles.update(self.svg.styles_from_templates(
            self._styles, self._style_defaults, self.options.__dict__))

        # Get a list of selected SVG shape elements and their transforms
        svg_elements = self.svg.get_shape_elements(self.get_elements())
        if not svg_elements:
            # Nothing selected or document is empty
            return

        # Create a new layer for the SVG output.
        if self.options.new_layer:
            new_layer = self.svg.create_layer(self._LAYER_NAME, incr_suffix=True)

        smoothness = self.options.smoothness / 100.0
        for element, element_transform in svg_elements:
            path = geomsvg.svg_element_to_geometry(
                       element, element_transform=element_transform)
            if path:
                new_path = self.smooth_path(path, smoothness)
                if self.options.new_layer:
                    parent = new_layer
                else:
                    parent = element.getparent()
                    parent.remove(element)
                style = None
                if self.options.match_style:
                    style = element.get('style')
                self._draw_path(new_path, style, parent)

    def smooth_path(self, path, smoothness=.5):
        """Create a smooth approximation of the path using Bezier curves.

        Args:
            path: A list of Line/Arc segments.
            smoothness: Smoothness value (usually between 0 and 1).
                .5 is a reasonable default.

        ReturnsL
            A list of CubicBezier segments.
        """
        new_path = []
        if len(path) < 2:
            return path
        seg1 = path[0]
        cp1 = seg1.p1
        for seg2 in path[1:]:
            curve, cp1 = bezier.smoothing_curve(seg1, seg2, cp1,
                                                smoothness=smoothness)
            new_path.append(curve)
            seg1 = seg2
        # Process last segment...
        if self._path_is_closed(path):
            seg2 = path[0]
            curve, cp1 = bezier.smoothing_curve(seg1, seg2, cp1,
                                                smoothness=smoothness)
            # Recalculate the first smoothing curve.
            curve0, cp1 = bezier.smoothing_curve(seg2, path[1], cp1,
                                                 smoothness=smoothness)
            # Replace first smoothing curve with the recalculated one.
            new_path[0] = curve0
        else:
            curve, unused = bezier.smoothing_curve(seg1, None, cp1,
                                                   smoothness=smoothness)
        new_path.append(curve)
        return new_path

    def _path_is_closed(self, path):
        """Return True if the path is closed."""
        return path[-1].p2 == path[0].p1

    def _draw_path(self, path, style, parent):
        """Draw the path as SVG."""
        if style is None:
            style = self._styles['polysmooth']
        _path_is_closed = self._path_is_closed(path)
        self.svg.create_polypath(path, style=style,
                                 close_path=_path_is_closed,
                                 parent=parent)


if __name__ == '__main__':
    ext = PolySmooth()
    ext.main(PolySmooth._OPTIONSPEC)
