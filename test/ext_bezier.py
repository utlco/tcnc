#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
Test various CubicBezier properties and methods.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division, unicode_literals)
# Uncomment this if any of these builtins are used.
# from future_builtins import (ascii, filter, hex, map, oct, zip)

import gettext
import logging

if __name__ == '__main__':
    import sys
    sys.path.append('../tcnc')

from inkscape import inkext
from tcnc import geom
from geom import bezier
from svg import geomsvg

__version__ = '0.2'

_ = gettext.gettext
logger = logging.getLogger(__name__)


class ExtBezier(inkext.InkscapeExtension):
    """An Inkscape extension that tests various CubicBezier
    properties and methods.
    """
    # Command line options
    OPTIONSPEC = (
        inkext.ExtOption('--tolerance', type='float', default=0.00001),
        inkext.ExtOption('--draw-inflections', type='inkbool', default=False),
        inkext.ExtOption('--draw-subdivide-inflections', type='inkbool', default=False),
        inkext.ExtOption('--draw-controlpoints', type='inkbool', default=False),
        inkext.ExtOption('--draw-biarcs', type='inkbool', default=False),
        inkext.ExtOption('--draw-normals', type='inkbool', default=False),
        inkext.ExtOption('--draw-t5', type='inkbool', default=False),
        inkext.ExtOption('--draw-extrema', type='inkbool', default=False),
        inkext.ExtOption('--draw-extrema-align', type='inkbool', default=False),
        inkext.ExtOption('--biarc-tolerance', type='docunits', default=0.01),
        inkext.ExtOption('--biarc-max-depth', type='int', default=4),
        inkext.ExtOption('--line-flatness', type='docunits', default=0.001),
    )

    _LAYER_NAME = 'bezier-test'
    _LINE_STYLE = 'fill:none;stroke:#000000;stroke-width:1px;stroke-opacity:1;'

    def run(self):
        """Main entry point for Inkscape extensions.
        """
        geom.debug.set_svg_context(self.svg)
        self.bezier_layer = self.svg.create_layer(self._LAYER_NAME)

        # Get a list of selected SVG shape elements and their transforms
        svg_elements = self.svg.get_shape_elements(self.get_elements())
        if not svg_elements:
            # Nothing selected or document is empty
            return
        # Convert SVG elements to path geometry
        path_list = geomsvg.svg_to_geometry(svg_elements)

        self.svg.set_default_parent(self.bezier_layer)
        if self.options.draw_controlpoints:
            self.controlpoint_layer = self.svg.create_layer('control points')
        if self.options.draw_inflections or self.options.draw_subdivide_inflections:
            self.inflection_layer = self.svg.create_layer('inflections')
        if self.options.draw_normals:
            self.normals_layer = self.svg.create_layer('normals')
        if self.options.draw_biarcs:
            self.biarc_layer = self.svg.create_layer('biarcs')
        for path in path_list:
            for segment in path:
                if isinstance(segment, bezier.CubicBezier):
                    self.draw_curve_attributes(segment)

    def draw_curve_attributes(self, curve):
        """
        """
        if self.options.draw_t5:
            self.draw_t5(curve)

        if self.options.draw_extrema:
            extrema = curve.find_extrema_points()
            if extrema:
                for p in extrema:
                    geom.debug.draw_point(p, color='#000000')
                extrema.append(curve.p1)
                extrema.append(curve.p2)
                bbox = geom.Box.from_points(extrema)
                geom.debug.draw_poly(bbox.vertices())


        if self.options.draw_extrema_align:
            extrema, bbox = curve.find_extrema_align()
            for p in extrema:
                geom.debug.draw_point(p, color='#000000')
            if bbox is not None:
                geom.debug.draw_poly(bbox)

        if self.options.draw_controlpoints:
            self.draw_control_points(curve, self.controlpoint_layer)
        if self.options.draw_subdivide_inflections:
            self.draw_subdivide_inflections(curve, self.inflection_layer)
        elif self.options.draw_inflections:
            self.draw_inflections(curve, self.inflection_layer)
        if self.options.draw_normals:
            self.draw_normals(curve, self.normals_layer)
        if self.options.draw_biarcs:
            self.draw_biarcs(curve,
                             self.options.biarc_tolerance,
                             self.options.biarc_max_depth,
                             self.options.line_flatness,
                             self.biarc_layer)

    def draw_t5(self, curve, layer=None):
        """
        """
        p = curve.point_at(0.5)
        geom.debug.draw_point(p, color='#c00000', parent=layer)

    def draw_control_points(self, curve, layer):
        # Draw control points
        tseg1 = geom.Line(curve.p1, curve.c1)
        geom.debug.draw_line(tseg1, color='#606060', parent=layer)
        tseg2 = geom.Line(curve.p2, curve.c2)
        geom.debug.draw_line(tseg2, color='#606060', parent=layer)
        geom.debug.draw_point(curve.p1, color='#606060', parent=layer)
        geom.debug.draw_point(curve.p2, color='#606060', parent=layer)
        geom.debug.draw_point(curve.c1, color='#606060', parent=layer)
        geom.debug.draw_point(curve.c2, color='#606060', parent=layer)

    def draw_subdivide_inflections(self, curve, layer):
        # Draw inflection points if any
        subcurves = curve.subdivide_inflections()
        logger.debug('subcurves=%d', len(subcurves))
        if len(subcurves) > 1:
            for subcurve in subcurves:
                geom.debug.draw_bezier(subcurve, color='#000000', parent=layer)
                self.draw_control_points(subcurve, layer=layer)

    def draw_inflections(self, curve, layer):
        # Draw inflection points if any
        t1, t2 = curve.find_inflections()
        if t1 > 0.0:
            ip1 = curve.point_at(t1)
            geom.debug.draw_point(ip1, color='#c00000', parent=layer)
        if t2 > 0.0:
            ip2 = curve.point_at(t2)
            geom.debug.draw_point(ip2, color='#c00000', parent=layer)

    def draw_normals(self, curve, layer):
        for i in range(101):
            t = i / 100.0
            normal = curve.normal(t)
            pt = curve.point_at(t)
            normal_line = geom.Line(pt, pt + normal)
            geom.debug.draw_line(normal_line, parent=layer)

    def draw_biarcs(self, curve, tolerance, max_depth,
                    line_flatness, layer):
        segments = curve.biarc_approximation(tolerance=tolerance,
                                             max_depth=max_depth,
                                             line_flatness=line_flatness)
        for segment in segments:
            if isinstance(segment, geom.Line):
                geom.debug.draw_line(segment, color='#00c000', parent=layer)
            elif isinstance(segment, geom.Arc):
                geom.debug.draw_arc(segment, color='#00c000', parent=layer)
            geom.debug.draw_point(segment.p1, color='#c000c0', parent=layer)
            geom.debug.draw_point(segment.p2, color='#c000c0', parent=layer)


if __name__ == '__main__':
    ExtBezier().main(ExtBezier.OPTIONSPEC)
