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

import geom.debug
from geom import bezier
from geom import transform2d
from geom import polygon
from inkscape import inkext
from svg import geomsvg

_ = gettext.gettext
logger = logging.getLogger(__name__)


class PolySmooth(inkext.InkscapeExtension):
    """An Inkscape extension that smoothes polygons.
    """
    # Command line options
    OPTIONSPEC = (
        inkext.ExtOption('--simplify', type='inkbool', default=False,
                         help=_('Simplify polylines first')),
        inkext.ExtOption('--simplify-tolerance', type='docunits',
                         default=.01,
                         help=_('Tolerance for simplification')),
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
#        if not self.options.new_layer:
#            # This will prevent the parent layer transform from being applied
#            # twice when the original element is replaced by the smoothed one.
#            parent_transform = transform2d.IDENTITY_MATRIX
        svg_elements = self.svg.get_shape_elements(
            self.get_elements(), parent_transform=parent_transform,
            accumulate_transform=self.options.new_layer)
        if not svg_elements:
            # Nothing selected or document is empty
            return

        # Create a new layer for the SVG output.
        if self.options.new_layer:
            new_layer = self.svg.create_layer(self._LAYER_NAME,
                                              incr_suffix=True)

        logger.debug('simpl: %f', self.options.simplify_tolerance)
        default_style = self._styles['polysmooth']
        smoothness = self.options.smoothness / 100.0
        for element, element_transform in svg_elements:
            # Convert the SVG element to Line/Arc/CubicBezier paths
            pathlist = geomsvg.svg_element_to_geometry(
                element, element_transform=element_transform)
            for path in pathlist:
                if self.options.simplify:
                    path = self.simplify_polylines(
                                path, self.options.simplify_tolerance)
                new_path = bezier.smooth_path(path, smoothness)
                if not new_path:
                    # Ignore failures and keep going...
                    # This should only happen if there are segments
                    # that are neither arc nor line.
                    continue
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

    def simplify_polylines(self, path, tolerance):
        """Simplify any polylines in the path.
        """
        new_path = []
        # Find polylines
        polyline = []
        for segment in path:
            if isinstance(segment, geom.Line):
                polyline.append(segment)
            elif len(polyline) > 1:
                # Simplify the polyline and then add it back to the path.
                polyline = self._simplify_polyline(polyline, tolerance)
                new_path.extend(polyline)
                # Reset accumulated polyline
                polyline = []
            else:
                new_path.append(segment)
        if polyline:
            polyline = self._simplify_polyline(polyline, tolerance)
            new_path.extend(polyline)
        return new_path

    def _simplify_polyline(self, path, tolerance):
        points1, points2 = zip(*path)
        points1 = list(points1)
#        points2 = list(points2)
#        points1.append(points2[-1])
        points1.append(path[-1][1])
        points = polygon.simplify_polyline_rdp(points1, tolerance)
        new_path = []
        prev_pt = points[0]
        for next_pt in points[1:]:
            next_line = geom.Line(prev_pt, next_pt)
            new_path.append(next_line)
            prev_pt = next_pt
        return new_path

if __name__ == '__main__':
    PolySmooth().main(PolySmooth.OPTIONSPEC)
