#!/usr/bin/env python
#
#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
An Inkscape extension to create a Voronoi diagram from
points derived from input SVG geometry.

====
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import gettext
import logging

import geom

from geom import planargraph
from geom import polygon
from geom import voronoi

from svg import geomsvg

from inkscape import inkext

__version__ = "0.2"

_ = gettext.gettext
logger = logging.getLogger(__name__)

_GEOM_EPSILON = 1e-09

class Voronoi(inkext.InkscapeExtension):
    """Inkscape plugin that creates Voronoi diagrams.
    """
    _OPTIONSPEC = (
        inkext.ExtOption('--epsilon', type='docunits', default=0.0001,
                         help='Epsilon'),
        inkext.ExtOption('--jiggle-points', '-j', type='inkbool', default=True,
                         help='Jiggle points.'),
        inkext.ExtOption('--delaunay-triangles', type='inkbool', default=False,
                         help='Delaunay triangles.'),
        inkext.ExtOption('--delaunay-edges', type='inkbool', default=False,
                         help='Delaunay edges.'),
        inkext.ExtOption('--clip-to-polygon', type='inkbool', default=False,
                         help='Clip to hull polygon.'),
    )

    _styles = {
        'voronoi':
            'fill:none;stroke-opacity:1.0;stroke-linejoin:round;'
            'stroke-width:${voronoi_stroke_width};'
            'stroke:${voronoi_stroke};',
        'delaunay':
            'fill:none;stroke-opacity:1.0;stroke-linejoin:round;'
            'stroke-width:${delaunay_stroke_width};'
            'stroke:${delaunay_stroke};',
        'delaunay_triangle':
            'stroke-opacity:1.0;stroke-linejoin:round;'
            'fill:${delaunay_triangle_fill};'
            'stroke-width:${delaunay_triangle_stroke_width};'
            'stroke:${delaunay_triangle_stroke};',
    }

    _STYLE_DEFAULTS = {
        'voronoi_stroke_width': '3pt',
        'voronoi_stroke': '#000000',
        'delaunay_stroke_width': '3pt',
        'delaunay_stroke': '#000000',
        'delaunay_triangle_fill': 'none',
        'delaunay_triangle_stroke_width': '1pt',
        'delaunay_triangle_stroke': '#000000',
    }

    def run(self):
        """Main entry point for Inkscape plugins.
        """
        geom.set_epsilon(_GEOM_EPSILON)
        geom.debug.set_svg_context(self.debug_svg)

        self._styles.update(self.svg.styles_from_templates(self._styles,
                                                          self._STYLE_DEFAULTS,
                                                          self.options.__dict__))

        # Get a list of selected SVG shape elements and their transforms
        svg_elements = self.svg.get_shape_elements(self.get_elements())
        if not svg_elements:
            # Nothing selected or document is empty
            return

        # Convert the SVG elements to segment geometry
        path_list = geomsvg.svg_to_geometry(svg_elements)

        # Create a set of input points from the segment end points
        input_points = set()
        polygon_segment_graph = planargraph.Graph()
        for path in path_list:
            for segment in path:
                input_points.add(segment.p1)
                input_points.add(segment.p2)
                polygon_segment_graph.add_edge(segment)

        self.clip_rect = geom.box.Box((0,0), self.svg.get_document_size())

        clipping_hull = None
        if self.options.clip_to_polygon:
            clipping_hull = polygon_segment_graph.boundary_polygon()

        voronoi_diagram = voronoi.VoronoiDiagram(
            list(input_points), do_delaunay=True,
            jiggle_points=self.options.jiggle_points)

        self._draw_voronoi(voronoi_diagram, clipping_hull)


    def _draw_voronoi(self, voronoi_diagram, clipping_hull):
        # Voronoi segments clipped to document
        voronoi_segments = self._clipped_voronoi_segments(voronoi_diagram,
                                                          self.clip_rect)
        # Voronoi segments clipped to polygon
        voronoi_clipped_segments = self._clipped_poly_voronoi_segments(
            voronoi_segments, clipping_hull)
        # Delaunay segments clipped to polygon
        delaunay_segments = self._clipped_delaunay_segments(voronoi_diagram,
                                                            clipping_hull)

        layer = self.svg.create_layer('voronoi_diagram', incr_suffix=True)
        style = self._styles['voronoi']
        for segment in voronoi_segments:
            self.svg.create_line(segment.p1, segment.p2, style=style,
                                 parent=layer)

        if clipping_hull is not None:
            layer = self.svg.create_layer('voronoi_clipped', incr_suffix=True)
            style = self._styles['voronoi']
            for segment in voronoi_clipped_segments:
                self.svg.create_line(segment.p1, segment.p2, style=style,
                                     parent=layer)
            voronoi_graph = planargraph.Graph(voronoi_clipped_segments)
            voronoi_graph.cull_open_edges()

            layer = self.svg.create_layer('voronoi_closed', incr_suffix=True)
            style = self._styles['voronoi']
            for segment in voronoi_graph.edges:
                self.svg.create_line(segment.p1, segment.p2, style=style,
                                     parent=layer)

        if self.options.delaunay_edges:
            layer = self.svg.create_layer('delaunay_edges', incr_suffix=True)
            style = self._styles['delaunay_triangle']
            for segment in delaunay_segments:
                self.svg.create_line(segment.p1, segment.p2, style=style,
                                     parent=layer)

        if self.options.delaunay_triangles:
            layer = self.svg.create_layer('delaunay_triangles', incr_suffix=True)
            for triangle in voronoi_diagram.triangles:
                self.svg.create_polygon(triangle, close_polygon=True,
                                    style=self._styles['delaunay_triangle'],
                                    parent=layer)

    def _clipped_voronoi_segments(self, diagram, clip_rect):
        """Clip a voronoi diagram to a clipping rectangle.

        Args:
            diagram: A VoronoiDiagram.
            clip_rect. A Box. Clipping rectangle.

        Returns:
            A list of (possibly) clipped voronoi segments.
        """
        voronoi_segments = []
        for edge in diagram.edges:
            p1 = edge.p1
            p2 = edge.p2
            if p1 is None or p2 is None:
                # The segment is missing an end point which means it's
                # is infinitely long so create an end point clipped to
                # the clipping rect bounds.
                if p2 is None:
                    # The line direction is right
                    xclip = clip_rect.xmax
                else:
                    # The line direction is left
                    p1 = p2
                    xclip = clip_rect.xmin
                # Ignore start points outside of clip rect.
                if not clip_rect.point_inside(p1):
                    continue
                a, b, c = edge.equation
                if geom.is_zero(b):#b == 0:
                    logger.debug('vert: a=%f, b=%f, c=%f, p1=%s, p2=%s',
                                 a, b, c, str(p1), str(p2))
                    # vertical line
                    x = c / a
                    center_y = (clip_rect.ymin + clip_rect.ymax) / 2
                    if p1[0] > center_y:
                        y = clip_rect.ymax
                    else:
                        y = clip_rect.ymin
                else:
                    x = xclip
                    y = (c - (x * a)) / b
                p2 = (x, y)
            line = clip_rect.clip_line(geom.Line(p1, p2))
            if line is not None:
                voronoi_segments.append(line)
        return voronoi_segments

    def _clipped_poly_voronoi_segments(self, voronoi_segments, clip_polygon):
        voronoi_clipped_segments = []
        for segment in voronoi_segments:
            if clip_polygon is not None:
                cliplines = polygon.intersect_line(clip_polygon, segment)
                for line in cliplines:
                    voronoi_clipped_segments.append(line)
        return voronoi_clipped_segments

    def _clipped_delaunay_segments(self, voronoi_diagram, clip_polygon):
        delaunay_segments = []
        for edge in voronoi_diagram.delaunay_edges:
            line = geom.Line(edge.p1, edge.p2)
            if (clip_polygon is None
                or self._line_inside_hull(clip_polygon, line, allow_hull=True)):
                delaunay_segments.append(line)
        return delaunay_segments

    def _line_inside_hull(self, points, line, allow_hull=False):
        """Test if line is inside or on the polygon defined by `points`.

        This is a special case.... basically the line segment will
        lie on the hull, have one endpoint on the hull, or lie completely
        within the hull, or be completely outside the hull. It will
        not intersect. This works for the Delaunay triangles and polygon
        segments...

        Args:
            points: polygon vertices. A list of 2-tuple (x, y) points.
            line: line segment to test.
            allow_hull: allow line segment to lie on hull

        Returns:
            True if line is inside or on the polygon defined by `points`.
            Otherwise False.
        """
        if allow_hull:
            for i in range(len(points)):
                pp1 = geom.P(points[i])
                pp2 = geom.P(points[i-1])
                if geom.Line(pp1, pp2) == line:
                    return True
        if not polygon.point_inside(points, line.midpoint()):
            return False
        p1 = line.p1
        p2 = line.p2
        if not allow_hull:
            for i in range(len(points)):
                pp1 = geom.P(points[i])
                pp2 = geom.P(points[i-1])
                if geom.Line(pp1, pp2) == line:
                    return False
        for i in range(len(points)):
            pp1 = geom.P(points[i])
            pp2 = geom.P(points[i-1])
            if p1 == pp1 or p1 == pp2 or p2 == pp1 or p2 == pp2:
                return True
        return (polygon.point_inside(points, p1)
                or polygon.point_inside(points, p2))


if __name__ == '__main__':
    plugin = Voronoi()
    plugin.main(Voronoi._OPTIONSPEC)
