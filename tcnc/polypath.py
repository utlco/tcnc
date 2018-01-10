#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
An Inkscape extension to create paths from a collection of vertices.

====
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import math
import random
import gettext
# import logging

import geom

from geom import planargraph
from geom import polygon
from geom import fillet

from svg import geomsvg
from inkscape import inkext

__version__ = "0.2"

_ = gettext.gettext
# logger = logging.getLogger(__name__)


class PolyPath(inkext.InkscapeExtension):
    """Inkscape plugin that traces paths on edge connected graphs.
    """
    OPTIONSPEC = (
        inkext.ExtOption('--epsilon', type='docunits', default=0.00001,
                         help='Epsilon'),
        inkext.ExtOption('--polysegpath-draw', type='inkbool', default=True,
                         help='Draw paths from polygon segments.'),
        inkext.ExtOption('--polysegpath-longest', type='inkbool', default=True,
                         help='Draw longest paths.'),
        inkext.ExtOption('--polysegpath-min-length', type='int', default=1,
                         help='Minimum number of path segments.'),
        inkext.ExtOption('--polysegpath-max', type='int', default=1,
                         help='Number of paths.'),
        inkext.ExtOption('--polysegpath-type', type='int', default=0,
                         help='Graph edge following strategy.'),
        inkext.ExtOption('--polysegpath-stroke', default='#000000',
                         help='Polygon CSS stroke color.'),
        inkext.ExtOption('--polysegpath-stroke-width', default='3px',
                         help='Polygon CSS stroke width.'),
        inkext.ExtOption('--polyoffset-draw', type='inkbool', default=True,
                         help='Create offset polygons.'),
        inkext.ExtOption('--polyoffset-recurs', type='inkbool', default=True,
                         help='Recursively offset polygons'),
        inkext.ExtOption('--polyoffset-jointype', type='int', default=0,
                         help='Join type.'),
        inkext.ExtOption('--polyoffset-offset', type='float', default=0,
                         help='Polygon offset.'),
        inkext.ExtOption('--polyoffset-fillet', type='inkbool', default=False,
                         help='Fillet offset polygons.'),
        inkext.ExtOption('--polyoffset-fillet-radius', type='float', default=0,
                         help='Offset polygon fillet radius.'),
        inkext.ExtOption('--convex-hull-draw', type='inkbool', default=True,
                         help='Draw convex hull.'),
        inkext.ExtOption('--hull-draw', type='inkbool', default=True,
                         help='Draw polyhull.'),
        inkext.ExtOption('--hull-inner-draw', type='inkbool', default=True,
                         help='Draw inner polyhulls.'),
        inkext.ExtOption('--hull-stroke', default='#000000',
                         help='Polygon CSS stroke color.'),
        inkext.ExtOption('--hull-stroke-width', default='3px',
                         help='Polygon CSS stroke width.'),
        inkext.ExtOption('--hull2-draw', type='inkbool', default=True,
                         help='Create expanded polyhull.'),
        inkext.ExtOption('--hull2-clip', type='inkbool', default=True,
                         help='Use expanded polyhull to clip.'),
        inkext.ExtOption('--hull2-draw-rays', type='inkbool', default=True,
                         help='Draw rays.'),
        inkext.ExtOption('--hull2-max-angle', type='degrees', default=180,
                         help='Max angle'),
    )

    _styles = {
        'dot':
            'fill:%s;stroke-width:1px;stroke:#000000;',
        'polyhull':
            'fill:none;stroke-opacity:1.0;stroke-linejoin:round;'
            'stroke-width:${polyhull_stroke_width};stroke:${polyhull_stroke};',
        'polychain':
            'fill:none;stroke-opacity:0.8;stroke-linejoin:round;'
            'stroke-width:${polychain_stroke_width};stroke:${polychain_stroke};',
        'polypath0':
            'fill:none;stroke-opacity:0.8;stroke-linejoin:round;'
            'stroke-width:${polypath_stroke_width};stroke:${polypath_stroke};',
        'polypath':
            'fill:none;stroke-opacity:0.8;stroke-linejoin:round;'
            'stroke-width:${polypath_stroke_width};stroke:${polypath_stroke};',
        'convexhull':
            'fill:none;stroke-opacity:1.0;stroke-linejoin:round;'
            'stroke-width:${convexhull_stroke_width};stroke:${convexhull_stroke};',
    }

    _style_defaults = {
        'polyhull_stroke_width': '3pt',
        'polyhull_stroke': '#505050',
        'polychain_stroke_width': '3pt',
        'polychain_stroke': '#00ff00',
        'polypath_stroke_width': '3pt',
        'polypath_stroke': '#3090c0',
        'convexhull_stroke_width': '3pt',
        'convexhull_stroke': '#ff9030',
    }

    def run(self):
        """Main entry point for Inkscape extension.
        """
        random.seed()

        geom.set_epsilon(self.options.epsilon)
        geom.debug.set_svg_context(self.debug_svg)

        styles = self.svg.styles_from_templates(self._styles,
                                                self._style_defaults,
                                                self.options.__dict__)
        self._styles.update(styles)

        # Get a list of selected SVG shape elements and their transforms
        svg_elements = self.svg.get_shape_elements(self.get_elements())
        if not svg_elements:
            # Nothing selected or document is empty
            return
        path_list = geomsvg.svg_to_geometry(svg_elements)

        # Create graph from geometry
        segment_graph = planargraph.Graph()
        for path in path_list:
            for segment in path:
                segment_graph.add_edge(segment)

        self.clip_rect = geom.box.Box((0, 0), self.svg.get_document_size())

        if self.options.polysegpath_draw or self.options.polysegpath_longest:
            path_builder = planargraph.GraphPathBuilder(segment_graph)
            if self.options.polysegpath_draw:
                self._draw_polypaths(path_builder)
            if self.options.polysegpath_longest:
                self._draw_longest_polypaths(path_builder)

        if self.options.polyoffset_draw:
            self._draw_offset_polygons(segment_graph)

        if self.options.convex_hull_draw:
            self._draw_convex_hull(segment_graph)

        if self.options.hull_draw:
            outer_hull = segment_graph.boundary_polygon()
            self._draw_polygon_hulls((outer_hull,))
            if self.options.hull_inner_draw:
                inner_hulls = segment_graph.peel_boundary_polygon(outer_hull)
                if inner_hulls:
                    self._draw_polygon_hulls(inner_hulls)

    def _draw_polypaths(self, path_builder):
        layer = self.svg.create_layer('q_polypath', incr_suffix=True)
        path_list = path_builder.build_paths(
                        path_strategy=self.options.polysegpath_type)
        for path in path_list:
            if len(path) > self.options.polysegpath_min_length:
                self.svg.create_polygon(path, close_polygon=False,
                                        style=self._styles['polypath'],
                                        parent=layer)

    def _draw_longest_polypaths(self, path_builder):
        path_list = path_builder.build_longest_paths(
                    path_strategy=self.options.polysegpath_type)
        for i, path in enumerate(path_list):
            if i == self.options.polysegpath_max:
                break
            layer = self.svg.create_layer('q_polypath_long_%d_' % i,
                                          incr_suffix=True)
            self.svg.create_polygon(path, close_polygon=False,
                                    style=self._styles['polypath'],
                                    parent=layer)

    def _draw_offset_polygons(self, graph):
        layer = self.svg.create_layer('q_cell_polygons', incr_suffix=True)
        polygons = graph.get_face_polygons()
        offset_polygons = self._offset_polys(polygons,
                                             self.options.polyoffset_offset,
                                             self.options.polyoffset_jointype,
                                             self.options.polyoffset_recurs)
        for poly in offset_polygons:
            if (self.options.polyoffset_fillet
                    and self.options.polyoffset_fillet_radius > 0):
                offset_path = fillet.fillet_polygon(poly,
                                    self.options.polyoffset_fillet_radius)
                self.svg.create_polypath(offset_path, close_path=True,
                                        style=self._styles['polypath'],
                                        parent=layer)
            else:
                self.svg.create_polygon(poly, close_path=True,
                                        style=self._styles['polypath'],
                                        parent=layer)
#        faces = graph.get_face_polygons()
#        for face_poly in faces:
#            offset_polys = polygon.offset_polygons(face_poly,
#                                                  self.options.polyoffset_offset)
#            for poly in offset_polys:
#                if (self.options.polyoffset_fillet
#                        and self.options.polyoffset_fillet_radius > 0):
#                    offset_path = fillet.fillet_polygon(poly,
#                                        self.options.polyoffset_fillet_radius)
#                    self.svg.create_polypath(offset_path, close_path=True,
#                                            style=self._styles['polypath'],
#                                            parent=layer)
#                else:
#                    self.svg.create_polygon(poly, close_path=True,
#                                            style=self._styles['polypath'],
#                                            parent=layer)

    def _offset_polys(self, polygons, offset, jointype, recurs=False):
        offset_polygons = []
        for poly in polygons:
            offset_polys = polygon.offset_polygons(poly, offset, jointype)
            offset_polygons.extend(offset_polys)
            if recurs:
                sub_offset_polys = self._offset_polys(offset_polys, offset,
                                                      jointype, True)
                offset_polygons.extend(sub_offset_polys)
        return offset_polygons

    def _draw_convex_hull(self, segment_graph):
        layer = self.svg.create_layer('q_convex_hull', incr_suffix=True)
        vertices = polygon.convex_hull(segment_graph.vertices())
        style = self._styles['convexhull']
        self.svg.create_polygon(vertices, style=style, parent=layer)

    def _draw_polygon_hulls(self, polygon_hulls):
        layer = self.svg.create_layer('q_polyhull', incr_suffix=True)
        for polyhull in polygon_hulls:
            self.svg.create_polygon(polyhull,
                                    style=self._styles['polyhull'], parent=layer)
        polyhull = polygon_hulls[0]

#         layer = self.svg.create_layer('q_polyhull2_triangles', incr_suffix=True)
#         concave_verts, polyhull2 = self._concave_vertices(polyhull, max_angle=math.pi/2)
#         for triangle in concave_verts:
#             self.svg.create_polygon(triangle, style=self._styles['polyhull'], parent=layer)
#
#         layer = self.svg.create_layer('q_polyhull2', incr_suffix=True)
#         self.svg.create_polygon(polyhull2,
#                                 style=self._styles['polyhull'], parent=layer)
#
#         layer = self.svg.create_layer('q_polyhull_rays', incr_suffix=True)
#         convex_verts = self._convex_vertices(polyhull)
#         rays = self._get_polygon_rays(convex_verts, self.clip_rect)
#         for ray in rays:
#             self.svg.create_line(ray.p1, ray.p2, style=self._styles['polyhull'],
#                                  parent=layer)
#
#         layer = self.svg.create_layer('q_polyhull2_rays', incr_suffix=True)
#         convex_verts = self._convex_vertices(polyhull2)
#         rays = self._get_polygon_rays(convex_verts, self.clip_rect)
#         for ray in rays:
#             self.svg.create_line(ray.p1, ray.p2, style=self._styles['polyhull'],
#                                  parent=layer)

    def _get_polygon_rays(self, vertices, clip_rect):
        """Return rays that emanate from convex vertices to the outside
        clipping rectangle.
        """
        rays = []
        for A, B, C in vertices:
            # Calculate the interior angle bisector segment
            # using the angle bisector theorem:
            # https://en.wikipedia.org/wiki/Angle_bisector_theorem
            AC = geom.Line(A, C)
            d1 = B.distance(C)
            d2 = B.distance(A)
            mu = d2 / (d1 + d2)
            D = AC.point_at(mu)
            bisector = geom.Line(D, B)
            # find the intersection with the clip rectangle
            dx = bisector.p2.x - bisector.p1.x
            dy = bisector.p2.y - bisector.p1.y
            # if dx is zero the line is vertical
            if geom.float_eq(dx, 0.0):
                y = clip_rect.ymax if dy > 0 else clip_rect.ymin
                x = bisector.p1.x
            else:
                # if slope is zero the line is horizontal
                m = dy / dx
                b = (m * -bisector.p1.x) + bisector.p1.y
                if dx > 0:
                    if geom.float_eq(m, 0.0):
                        y = b
                        x = clip_rect.xmax
                    else:
                        y = clip_rect.xmax * m + b
                        if m > 0:
                            y = min(clip_rect.ymax, y)
                        else:
                            y = max(clip_rect.ymin, y)
                        x = (y - b) / m
                else:
                    if geom.float_eq(m, 0.0):
                        y = b
                        x = self.clip_rect.xmin
                    else:
                        y = self.clip_rect.xmin * m + b
                        if m < 0:
                            y = min(clip_rect.ymax, y)
                        else:
                            y = max(clip_rect.ymin, y)
                        x = (y - b) / m
            clip_pt = geom.P(x, y)
            rays.append(geom.Line(bisector.p2, clip_pt))
        return rays

    def _convex_vertices(self, vertices):
        """
        :param vertices: the polygon vertices. An iterable of 2-tuple (x, y) points.
        :return: A list of triplet vertices that are pointy towards the outside.
        """
        pointy_verts = []
        clockwise = polygon.area(vertices) < 0
        i = -3 if vertices[-1] == vertices[0] else -2
        vert1 = vertices[i]
        vert2 = vertices[i + 1]
        for vert3 in vertices:
            seg = geom.Line(vert1, vert2)
            side = seg.which_side(vert3, inline=True)
            if side != 0 and ((clockwise and side > 0) or (not clockwise and side < 0)):
                pointy_verts.append((vert1, vert2, vert3))
            vert1 = vert2
            vert2 = vert3
        return pointy_verts

    def _concave_vertices(self, vertices, max_angle=math.pi):
        """
        Args:
            vertices: the polygon vertices. An iterable of
                2-tuple (x, y) points.
            max_angle: Maximum interior angle of the concave vertices.
                Only concave vertices with an interior angle less
                than this will be returned.

        Returns:
            A list of triplet vertices that are pointy towards the inside
            and a new, somewhat more convex, polygon with the concave
            vertices closed.
        """
        concave_verts = []
        new_polygon = []
        clockwise = polygon.area(vertices) < 0
        i = -3 if vertices[-1] == vertices[0] else -2
        vert1 = vertices[i]
        vert2 = vertices[i + 1]
        for vert3 in vertices:
            seg = geom.Line(vert1, vert2)
            side = seg.which_side(vert3)
            angle = abs(vert2.angle2(vert1, vert3))
            if angle < max_angle and ((clockwise and side < 0) or (not clockwise and side > 0)):
                concave_verts.append((vert1, vert2, vert3))
                new_polygon.append(vert3)
            elif not new_polygon or vert2 != new_polygon[-1]:
                new_polygon.append(vert2)
            vert1 = vert2
            vert2 = vert3
        return (concave_verts, new_polygon)


if __name__ == '__main__':
    PolyPath().main(optionspec=PolyPath.OPTIONSPEC)
