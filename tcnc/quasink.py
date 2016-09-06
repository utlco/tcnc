#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
An Inkscape extension to create quasicrystalline/Penrose tesselations.

====
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import sys
import math
import random
import gettext
import logging

import geom
from geom import quasi
from geom import planargraph
from geom import transform2d
from geom import polygon

from inkscape import inkext

__version__ = "0.2"

_ = gettext.gettext
logger = logging.getLogger(__name__)

class IdentityProjector(object):
    """Identity projection. No distortion."""
    def project(self, p):
        return p

class SphericalProjector(IdentityProjector):
    """Project a point on to a sphere."""
    def __init__(self, center, radius, invert=False):
        self.center = center
        self.radius = radius
        self.invert = invert

    def project(self, p):
        v = p - self.center
        h = v.length()
        if h > self.radius:
            return p
        scale = math.sin((h * (math.pi / 2)) / self.radius)
        if not self.invert:
            scale = (self.radius * scale) / h
        return (v * scale) + self.center


class QuasiExtension(inkext.InkscapeExtension):
    """Inkscape plugin that creates quasi-crystal-like patterns.
    Based on quasi.c by Eric Weeks.
    """
    _styles = {
        'infotext':
            'font-size:.2;font-style:normal;font-weight:normal;'
            'line-height:125%;letter-spacing:0px;word-spacing:0px;'
            'fill:#000000;fill-opacity:1;stroke:none;font-family:Sans',
        'dot':
            'fill:%s;stroke-width:.2;stroke:#000000;',
        'frame':
            'fill:none;stroke-width:%s;stroke:#504030;',
        'margins':
            'fill:none;stroke-width:.1;stroke:#3030ff;',
        'bbox':
            'fill:none;stroke-width:.1;stroke:#30f090;',
        'polygon':
            'stroke-opacity:1.0;stroke-linejoin:round;'
            'stroke-width:$polygon_stroke_width;stroke:$polygon_stroke;',
        'polygon_filled':
            'fill:%s;stroke:%s;stroke-width:$polygon_fill_stroke_width;',
        'polygon_circle':
            'stroke-opacity:1.0;stroke-linejoin:round;'
            'fill:none;stroke-width:.1;stroke:#903030;',
        'polygon_ellipse':
            'stroke-opacity:1.0;stroke-linejoin:round;'
            'fill:none;stroke-width:.1;stroke:#306060;',
        'polyseg':
            'fill:none;stroke-opacity:0.8;'
            'stroke-width:$polyseg_stroke_width;stroke:$polyseg_stroke;',
        'polyseg_color':
            'fill:none;stroke-opacity:0.8;'
            'stroke-width:$polyseg_stroke_width;stroke:%s;',
        'segment':
            'fill:none;stroke-opacity:0.8;'
            'stroke-width:$segment_stroke_width;stroke:$segment_stroke;',
        'segchain':
            'fill:%s;fill-opacity:0.5;stroke-opacity:0.75;stroke-linejoin:round;'
            'stroke-width:$segchain_stroke_width;stroke:$segchain_stroke;',
    }
    _style_defaults = {
        'infotext_size': '12pt',
        'margin_stroke_width': '.1in',
        'margin_stroke': '#000000',
        'polygon_fill_stroke_width': '1px',
        'polygon_stroke_width': '3pt',
        'polygon_stroke': '#00ff00',
        'polyseg_stroke_width': '.1in',
        'polyseg_stroke': '#000000',
        'segment_stroke_width': '3pt',
        'segment_stroke': '#000000',
        'segchain_stroke_width': '1pt',
        'segchain_stroke': '#000000',
    }

    _FILL_LUT = {
                'none': ('#808080',),
                'cmy': ('#00FFFF', '#FF00FF', '#FFFF00'),
                'rgb': ('#FF0000', '#00FF00', '#0000FF'),
                'rainbow': ('#FF0000', '#FF7F00', '#FFFF00', '#00FF00',
                            '#0000FF', '#4B0082', '#8B00FF'),
                # Gray 5% increments
                'gray05': ('#f2f2f2', '#e6e6e6', '#d9d9d9', '#cccccc',
                           '#bfbfbf', '#b3b3b3', '#a6a6a6', '#999999',
                           '#8c8c8c', '#808080', '#737373', '#666666',
                           '#595959', '#4d4d4d', '#404040', '#333333',
                           '#262626', '#1a1a1a', '#0d0d0d', '#000000'),
                # Gray 10% increments
                'gray10': ('#e6e6e6', '#cccccc', '#b3b3b3', '#999999',
                           '#808080', '#666666', '#4d4d4d', '#333333',
                           '#1a1a1a', '#000000'),

                'red05': ('#ffe5e5', '#ffcccc', '#ffb3b3', '#ff9999',
                          '#ff8080', '#ff6666', '#ff4d4d', '#ff3333',
                          '#ff1a1a', '#ff0000', '#e60000', '#cc0000',
                          '#b30000', '#990000', '#800000', '#660000',
                          '#4d0000', '#330000', '#1a0000', '#000000'),

                'red10': ('#ffcccc', '#ff9999', '#ff6666', '#ff3333',
                          '#ff0000', '#cc0000', '#990000', '#660000',
                          '#330000', '#000000'),

                'green10': ('#ccffcc', '#99ff99', '#66ff66', '#45ff45',
                            '#00ff00', '#00ee20', '#00dd00', '#00bb00',
                            '#009900', '#007700', '#006600',
                            '#003300', '#000000'),

                'yellow05': ('#fffde5', '#fffacc', '#fff8b3', '#fff599',
                             '#fff380', '#fff166', '#ffee4d', '#ffec33',
                             '#ffe91a', '#ffe700', '#e6d000', '#ccb900',
                             '#b3a200', '#998b00', '#807300', '#665c00',
                             '#4d4500', '#332e00', '#1a1700', '#000000',),

                'yellow10': ('#fffde5', '#fff8b3', '#fff380', '#ffee4d',
                             '#ffe91a', '#e6d000', '#b3a200', '#807300',
                             '#4d4500', '#4d4500', '#1a1700',),

                'gray': [],
                'red': [],
                'yellow': [],
                'green': [],
                'blue': [],
    }

    POLYGON_SORT_NONE, \
    POLYGON_SORT_INSIDE_OUT, \
    POLYGON_SORT_OUTSIDE_IN = range(3)

    # Scale multiplier. This should be about right to get the whole
    # thing on a A4 size sheet of paper at 1.0 scale.
    _SCALE_SCALE = .1

    def run(self):
        """Main entry point for Inkscape plugins.
        """
        random.seed()
        geom.set_epsilon(self.options.epsilon)
        geom.debug.set_svg_context(self.debug_svg)

        doc_size = geom.P(self.svg.get_document_size())
        self.doc_center = doc_size / 2

        # Determine clipping rectangle which is bounded by the document
        # or the margins, depending on user options. The margins can
        # be outside the document bounds.
        # (Y axis is inverted in Inkscape)
        clip_rect = None # Default
        bottom_left = geom.P(self.options.margin_left, self.options.margin_top)
        top_right = doc_size - geom.P(self.options.margin_right,
                                     self.options.margin_bottom)
        self.margin_clip_rect = geom.box.Box(bottom_left, top_right)
        doc_clip_rect = geom.box.Box(geom.P(0,0), doc_size)
        if self.options.clip_to_doc and self.options.clip_to_margins:
            clip_rect = doc_clip_rect.intersection(self.margin_clip_rect)
        elif self.options.clip_to_doc:
            clip_rect = doc_clip_rect
        elif self.options.clip_to_margins:
            clip_rect = self.margin_clip_rect

        # The clipping region can be a circle or a rectangle
        if clip_rect is not None and self.options.clip_to_circle:
            radius = min(clip_rect.width(), clip_rect.height()) / 2.0
            self.clip_region = geom.ellipse.Ellipse(clip_rect.center(), radius)
        else:
            self.clip_region = clip_rect

        if self.options.clip_offset_center:
            clip_offset = clip_rect.center() - self.doc_center
            self.options.offset_x += clip_offset.x
            self.options.offset_y += clip_offset.y

        # Optionally insert spherical point projection
        if self.options.project_sphere:
            projector = SphericalProjector(self.doc_center,
                                                self.options.project_radius,
                                                invert=self.options.project_invert)
        else:
            projector = IdentityProjector()
        # Set up plotter transform for rotation, scale, and offset.
        # Origin at document center.
        scale = self.options.scale * self._SCALE_SCALE
        offset = geom.P(self.doc_center) + geom.P(self.options.offset_x,
                                                  self.options.offset_y)
        transform1 = transform2d.matrix_rotate(self.options.rotate)
        transform2 = transform2d.matrix_scale_translate(scale, scale,
                                                        offset.x, offset.y)
        plot_transform = transform2d.compose_transform(transform1, transform2)
        plotter = _QuasiPlotter(self.clip_region, plot_transform, projector)

        # Create color LUTs
        for i in range(255):
            ci = 255 - i
            self._FILL_LUT['red'].append('#%02x0000' % ci)
            self._FILL_LUT['yellow'].append('#%02x%02x00' % (ci, ci))

        q = quasi.Quasi()
        q.offset_salt_x = self.options.salt_x
        q.offset_salt_y = self.options.salt_y
        q.skinnyfat_ratio = self.options.skinnyfat_ratio
        q.segment_ratio = self.options.segment_ratio
        q.segtype_skinny = self.options.segtype_skinny
        q.segtype_fat = self.options.segtype_fat
        q.segment_split_cross = self.options.segment_split_cross
        q.symmetry = self.options.symmetry
        q.numlines = self.options.numlines
        q.plotter = plotter
        q.color_fill = self.options.polygon_fill
        q.color_by_polytype = self.options.polygon_zfill
        q.quasi()

        # Re-center the quasi polygons to the clip region borders
        if self.options.clip_recenter and self.clip_region is not None:
            q.plotter.recenter()

        polygon_segment_graph = planargraph.Graph()
        for poly in q.plotter.polygons:
            polygon_segment_graph.add_poly(poly)
        polygon_segments = list(polygon_segment_graph.edges)

        # Optionally sort the polygons to change drawing order.
        if self.options.polygon_sort != self.POLYGON_SORT_NONE:
            outer_hull = polygon_segment_graph.boundary_polygon()
            hull_centroid = polygon.centroid(outer_hull)
            # Find the distance of the farthest polygon
            max_d = 0.0
            for poly in q.plotter.polygons:
                d = hull_centroid.distance(polygon.centroid(poly))
                if d > max_d:
                    max_d = d
            segment_size = q.plotter.polygons[0][0].distance(q.plotter.polygons[0][1])

            # Secondary sort key is angular location
            angle_key = lambda poly: hull_centroid.ccw_angle2(hull_centroid + geom.P(1, 0), polygon.centroid(poly))
            q.plotter.polygons.sort(key=angle_key)
            angle_key = lambda segment: hull_centroid.ccw_angle2(hull_centroid + geom.P(1, 0), segment.midpoint())
            polygon_segments.sort(key=angle_key)
            q.plotter.segments.sort(key=angle_key)

            # Primary sort key is distance from centroid
            dist_key = lambda poly: int(hull_centroid.distance(polygon.centroid(poly)) / segment_size)
            dist_key2 = lambda segment: int(hull_centroid.distance(segment.midpoint()) / segment_size)
            if self.options.polygon_sort == self.POLYGON_SORT_INSIDE_OUT:
                q.plotter.polygons.sort(key=dist_key)
                polygon_segments.sort(key=dist_key2)
                q.plotter.segments.sort(key=dist_key2)
            elif self.options.polygon_sort == self.POLYGON_SORT_OUTSIDE_IN:
                q.plotter.polygons.sort(key=dist_key, reverse=True)
                polygon_segments.sort(key=dist_key2, reverse=True)
                q.plotter.segments.sort(key=dist_key2, reverse=True)
#             angle_key = lambda poly: hull_centroid.ccw_angle2(hull_centroid + geom.P(1, 0), polygon.centroid(poly))
#             q.plotter.polygons.sort(key=angle_key)
#             angle_key = lambda segment: hull_centroid.ccw_angle2(hull_centroid + geom.P(1, 0), segment.midpoint())
#             polygon_segments.sort(key=angle_key)


        self._styles.update(self.svg.styles_from_templates(self._styles,
                                                          self._style_defaults,
                                                          self.options.__dict__))

        logger.debug('colors: %d' % len(plotter.color_count))
        for color in sorted(plotter.color_count.keys()):
            logger.debug('[%.5f]: %d' % (color, plotter.color_count[color]))

        if self.options.create_info_layer:
            self._draw_info_layer()

        if self.options.margin_draw:
            self._draw_margins(q.plotter.bbox())

        if self.options.polygon_draw:
            self._draw_polygons(q.plotter)
#            self._draw_polygon_circles(q.plotter.polygons)

        if self.options.polyseg_draw:
            self._draw_polygon_segments(polygon_segments)

        if self.options.polygon_mult > 0:
            self._draw_inset_polygons(q.plotter.polygons,
                                       self.options.polygon_mult_spacing,
                                       self.options.polygon_mult)

        if self.options.ellipse_draw:
            self._draw_polygon_ellipses(q.plotter.polygons,
                                        self.options.ellipse_inset)

        if self.options.segtype_skinny == quasi.Quasi.SEG_NONE \
        and self.options.segtype_fat == quasi.Quasi.SEG_NONE:
            self.options.segment_draw = False
            self.options.segpath_draw = False

        if self.options.segment_draw:
            self._draw_segments(q.plotter.segments)

        if self.options.segpath_draw:
            self._draw_segment_chains(q.plotter.segments)

        if self.options.frame_draw and (self.options.frame_width > 0 and
                                        self.options.frame_height > 0):
            self._draw_frame()

    def _draw_info_layer(self):
        """Draw some info about this tesselation."""
        layer = self.svg.create_layer('q_info')
        info = ('Symmetry: %d' % self.options.symmetry,
                'Scale: %.1f' % self.options.scale,
                'Rotation: %.2f' % math.degrees(self.options.rotate),
                'Offset X: %.2f' % self.options.offset_x,
                'Offset Y: %.2f' % self.options.offset_y,
                'Skinny-fat ratio: %.2f' % self.options.skinnyfat_ratio,
                'Segment ratio: %.2f' % self.options.segment_ratio,
                'Num lines: %d' % self.options.numlines,
                'Salt X: %.5f' % self.options.salt_x,
                'Salt Y: %.5f' % self.options.salt_y,
                'Epsilon: %.5f' % self.options.epsilon,
                'Margins: T%.2f, L%.2f, R%.2f, B%.2f' % (self.options.margin_top,
                                                 self.options.margin_left,
                                                 self.options.margin_right,
                                                 self.options.margin_bottom),
                'Polygon sort: %d' % self.options.polygon_sort,
                )
        self.svg.create_text(info, self.svg.unit2uu('10px'),
                             self.svg.unit2uu('30px'),
                             line_height=self.svg.unit2uu('25px'),
                             style=self._styles['infotext'],
                             parent=layer)


    def _draw_margins(self, bbox):
        layer = self.svg.create_layer('q_margins')
        if isinstance(self.clip_region, geom.ellipse.Ellipse):
            self.svg.create_ellipse(self.clip_region.center,
                                    self.clip_region.rx, self.clip_region.ry,
                                    angle = 0.0,
                                    style=self._styles['margins'], parent=layer)
        else:
            margin_vertices = [self.clip_region.p1,
                               geom.P(self.clip_region.p1.x,
                                      self.clip_region.p2.y),
                               self.clip_region.p2,
                               geom.P(self.clip_region.p2.x,
                                      self.clip_region.p1.y),
                               ]
            self.svg.create_polygon(margin_vertices,
                                    style=self._styles['margins'], parent=layer)
        bbox_vertices = [bbox.p1, geom.P(bbox.p1.x, bbox.p2.y),
                         bbox.p2, geom.P(bbox.p2.x, bbox.p1.y)]
        self.svg.create_polygon(bbox_vertices,
                                style=self._styles['bbox'], parent=layer)

    def _draw_frame(self):
        layer = self.svg.create_layer('q_frame')
        offset  = self.options.frame_thickness / 2
        cx = self.options.frame_width / 2 + offset
        cy = self.options.frame_height / 2 + offset
        frame_vertices = [self.doc_center + geom.P(cx, cy),
                          self.doc_center + geom.P(cx, -cy),
                          self.doc_center + geom.P(-cx, -cy),
                          self.doc_center + geom.P(-cx, cy)]
        style = self._styles['frame'] % self.options.frame_thickness
        self.svg.create_polygon(frame_vertices,
                                style=style, parent=layer)

    def _draw_polygons(self, plotter):
        polygon_list = plotter.polygons
        layer1_name = 'q_polygons_%d' % self.options.symmetry
        layer1 = self.svg.create_layer(layer1_name, incr_suffix=True)
#         if self.options.create_culledrhombus_layer:
#             layer2_name = 'q_polygons_x_%d' % self.options.symmetry
#             layer2 = self.svg.create_layer(layer2_name, incr_suffix=True)
#         if self.options.polygon_fill and self.options.polygon_stroke == 'none':
        if self.options.polygon_fill:
            fill_lut = self._FILL_LUT[self.options.polygon_fill_lut]
            fill_lut_offset = self.options.polygon_fill_lut_offset
            fill_style_template = self._styles['polygon_filled']
            fill_colors = sorted(plotter.color_count.keys())
        else:
            style = self._styles['polygon']
        color_index = 0
        for i, vertices in enumerate(polygon_list):
            if self.options.polygon_fill:
                if self.options.polygon_zfill:
                    color = plotter.polygon_colors[i]
                    color_index = fill_colors.index(color)
#                     color_index = int(len(fill_lut) * color / 2)
                else:
                    color_index = (color_index + 1)
                color_index = (color_index + fill_lut_offset) % len(fill_lut)
                css_color = fill_lut[color_index]
                style = fill_style_template % (css_color, css_color)
            self.svg.create_polygon(vertices, style=style, parent=layer1)
#             if self.options.create_culledrhombus_layer:
#                 d1 = vertices[0].distance(vertices[2])
#                 d2 = vertices[1].distance(vertices[3])
#                 if self.options.min_rhombus_width < min(d1, d2):
#                     style = self._styles['polygon'] % (fill_lut[color_index],)
#                     self.svg.create_polygon(vertices, style=style, parent=layer2)

    def _draw_inset_polygons(self, polygon_list, offset, nmax=1):
        style = self._styles['polygon'] % ('none',)
        offset_total = offset
        for n in range(nmax):
            layer = self.svg.create_layer('q_insetpolygons_%d' % (n+1,),
                                          incr_suffix=True)
            for vertices in polygon_list:
                vertices = self._inset_polygon(vertices, offset_total)
                if vertices is not None:
                    self.svg.create_polygon(vertices, style=style, parent=layer)
            offset_total += offset

    def _inset_polygon(self, vertices, offset):
        """Inset the polygon by the amount :offset:"""
        L1 = geom.Line(vertices[0], vertices[1])
        L2 = geom.Line(vertices[1], vertices[2])
        L3 = geom.Line(vertices[2], vertices[3])
        L4 = geom.Line(vertices[3], vertices[0])
        d1 = L1.distance_to_point(L3.p1)
        d2 = L2.distance_to_point(L1.p1)
        if d1 >= offset*2 and d2 >= offset*2:
            offset *= L1.which_side(L2.p2)
            L1_o = L1.offset(offset)
            L2_o = L2.offset(offset)
            L3_o = L3.offset(offset)
            L4_o = L4.offset(offset)
            p1 = L4_o.intersection(L1_o)
            p2 = L1_o.intersection(L2_o)
            p3 = L2_o.intersection(L3_o)
            p4 = L3_o.intersection(L4_o)
            return (p1, p2, p3, p4)
        return None

    def _draw_polygon_circles(self, polygon_list):
        layer = self.svg.create_layer('q_polygon_circles', incr_suffix=True)
        style = self._styles['polygon_circle']
        for poly in polygon_list:
            center = geom.Line(poly[0], poly[2]).midpoint()
            a = abs(poly[1].angle2(poly[0], poly[2]))
            radius = math.sin(a) * poly[1].distance(poly[2]) / 2
#            if a > math.pi:
#                radius = math.sin(a - math.pi) * poly[0].distance(poly[1]) / 2
#            else:
#                radius = math.sin(a) * poly[1].distance(poly[2]) / 2
            self.svg.create_circle(center, radius, style=style, parent=layer)

    def _draw_polygon_ellipses(self, polygon_list, inset):
        layer = self.svg.create_layer('q_polygon_ellipses', incr_suffix=True)
        style = self._styles['polygon_ellipse']
        for poly in polygon_list:
            e = geom.ellipse.ellipse_in_parallelogram(poly)
            self.svg.create_ellipse(e.center, e.rx - inset, e.ry - inset,
                                    e.phi, style=style, parent=layer)

    def _draw_polygon_segments(self, segment_list):
        fill_lut = self._FILL_LUT[self.options.polyseg_lut]
        if self.options.polyseg_layer_per_color:
            layers = []
            for i in range(len(fill_lut)):
                layer = self.svg.create_layer('q_polyseg_%d' % i,
                                              incr_suffix=True)
                layers.append(layer)
        else:
            layer = self.svg.create_layer('q_polysegs', incr_suffix=True)
        color_index = 0
        for segment in segment_list:
            if self.options.polyseg_scale != 1.0:
                seglen = segment.length()
                ext = (seglen * self.options.polyseg_scale) - seglen
                segment = segment.extend(ext, from_midpoint=True)
            if self.options.polyseg_clip_to_margins:
                segment = self.margin_clip_rect.clip_line(segment)
            style=self._styles['polyseg_color'] % fill_lut[color_index]
            color_index = (color_index + 1) % len(fill_lut)
            if self.options.polyseg_layer_per_color:
                layer = layers[color_index]
            self.svg.create_line(segment.p1, segment.p2, style=style,
                                 parent=layer)

    def _draw_segments(self, segment_list):
        layer = self.svg.create_layer('q_segments', incr_suffix=True)
        for segment in segment_list:
            if self.options.segment_scale != 1.0:
                seglen = segment.length()
                ext = (seglen * self.options.segment_scale) - seglen
                segment = segment.extend(ext, from_midpoint=True)
            self.svg.create_line(segment.p1, segment.p2,
                                 style=self._styles['segment'],
                                 parent=layer)

    def _draw_segment_chains(self, segment_list):
        layer = self.svg.create_layer('q_segment_chains', incr_suffix=True)
        chain_list = self._create_chains(segment_list)
        # Sort segment paths so that the largest are at the bottom of the Z-order
        key = lambda v: abs(polygon.area(v))
        chain_list.sort(key=key, reverse=True)
        for vertices in chain_list:
            if self.options.segpath_fillclosed and polygon.is_closed(vertices):
                style = self._styles['segchain'] % '#c0c0c0'
            else:
                style = self._styles['segchain'] % 'none'
            if not self.options.segpath_closed or polygon.is_closed(vertices):
                self.svg.create_polygon(vertices, close_polygon=False,
                                        close_path=True, style=style,
                                        parent=layer)

    def _create_chains(self, segments):
        chain_list = []
        while segments:
            chain = _SegmentChain()
            n = 1
            while n > 0:
                unchained_segments = []
                for segment in segments:
                    if not chain.connect_segment(segment):
                        unchained_segments.append(segment)
                n = len(segments) - len(unchained_segments)
                segments = unchained_segments
            if chain:
                chain_list.append(chain.polyline())
        return chain_list


class _SegmentChain(list):
    """A simple polygonal chain as a series of connected line segments.
    """
    def __init__(self, min_corner_angle=0.0):
        self.min_corner_angle = min_corner_angle

    @property
    def startp(self):
        return self[0].p1

    @property
    def endp(self):
        return self[-1].p2

    def connect_segment(self, segment):
        """Try to connect the segment to the chain.
        :return: True if successful otherwise False.
        """
        if len(self) == 0:
            self.append(segment)
            return True
        if segment.p1 == self.endp:
            return self._append_segment(segment)
        elif segment.p2 == self.endp:
            return self._append_segment(segment.reversed())
        elif segment.p2 == self.startp:
            return self._prepend_segment(segment)
        elif segment.p1 == self.startp:
            return self._prepend_segment(segment.reversed())
        else:
            return False

    def polyline(self):
        """Return a list of vertices.
        """
        vertices = [self[0].p1]
        for segment in self:
            vertices.append(segment.p2)
        return vertices

    def _prepend_segment(self, segment):
        angle_ok =  self._angle_is_ok(segment, self[0])
        if angle_ok:
            self.insert(0, segment)
        return angle_ok

    def _append_segment(self, segment):
        angle_ok = self._angle_is_ok(self[-1], segment)
        if angle_ok:
            self.append(segment)
        return angle_ok

    def _angle_is_ok(self, seg1, seg2):
        return (self.min_corner_angle <= 0.0 or
                abs(seg1.p2.angle2(seg1.p1, seg2.p2)) > self.min_corner_angle)


class _QuasiPlotter(quasi.QuasiPlotter):
    """Accumulates the quasi geometry. Also transforms and clips.
    """
    def __init__(self, clip_region, transform_matrix, projector, clip_all=True):
        """
        :param clip_region: The clipping region
        :param transform_matrix: All objects will be tranformed using
        this transform matrix.
        :param projector: All objects will be transformed using this projector.
        :param clip_all: If true the entire polygon or segment will not be plotted
        if any part of it is clipped.
        """
        self.polygons = []
        self.polygon_colors = []
        self.segments = []
        self.clip_region = clip_region
        self.transform_matrix = transform_matrix
        self.clip_all = clip_all
        if projector is None:
            self.projector = IdentityProjector()
        else:
            self.projector = projector
        self._xmin = sys.float_info.max
        self._ymin = sys.float_info.max
        self._xmax = sys.float_info.min
        self._ymax = sys.float_info.min

#         # Color index incr
#         self.color_index = 0
#         # Map of color to color_index
#         self.color_map = {}
        # Count of polygons in each color
        self.color_count = {}

    def plot_polygon(self, vertices, color):
        """
        """
        assert(0.0 <= color <= 1.0)
        xvertices = []
        clip_count = 0
        for vertex in vertices:
            p = transform2d.matrix_apply_to_point(self.transform_matrix, vertex)
            p = self.projector.project(geom.P(p))
            xvertices.append(p)
            if self.clip_region and not self.clip_region.point_inside(p):
                clip_count += 1
        if (self.clip_all and clip_count > 0) or clip_count > 3:
            return False
        self._update_bbox(xvertices)
        self.polygons.append(xvertices)
#         if color in self.color_map:
#             color_index = self.color_map[color]
#             self.color_count[color_index] += 1
#         else:
#             self.color_map[color] = self.color_index
#             self.color_count[self.color_index] = 1
#             color_index = self.color_index
#             self.color_index += 1
#         assert(color > 0.0 and color < 1.0)
        if color in self.color_count:
            self.color_count[color] += 1
        else:
            self.color_count[color] = 1
        self.polygon_colors.append(color)
        return True

    def plot_segment(self, p1, p2):
        p1 = self.projector.project(geom.P(p1).transform(self.transform_matrix))
        p2 = self.projector.project(geom.P(p2).transform(self.transform_matrix))
#         if self.clip_region is None or (self.clip_region.point_inside(p1) and
#                                         self.clip_region.point_inside(p1)):
        self.segments.append(geom.Line(p1, p2))

    def recenter(self):
        """Re-center the polygons and segments so the bounding box is centered
        within the clipping region.
        """
        if self.clip_region is None:
            return
        cx = (self._xmax - self._xmin) / 2
        cy = (self._ymax - self._ymin) / 2
        bbox_center = geom.P(self._xmin + cx, self._ymin + cy)
        offset = self.clip_region.center - bbox_center
        centered_polygons = []
        centered_segments = []
        for poly in self.polygons:
            new_poly = []
            for p in poly:
                new_poly.append(p + offset)
            centered_polygons.append(new_poly)
        for segment in self.segments:
            offset_segment = geom.Line(segment.p1 + offset, segment.p2 + offset)
            centered_segments.append(offset_segment)
        self.segments = centered_segments
        self.polygons = centered_polygons
        self._xmin += offset.x
        self._xmax += offset.x
        self._ymin += offset.y
        self._ymax += offset.y

    def bbox(self):
        """Bounding box.
        """
        return geom.Box(geom.P(self._xmin, self._ymin),
                        geom.P(self._xmax, self._ymax))

    def _update_bbox(self, points):
        """Update the bounding box with the given vertex point."""
        for p in points:
            self._xmin = min(self._xmin, p.x)
            self._ymin = min(self._ymin, p.y)
            self._xmax = max(self._xmax, p.x)
            self._ymax = max(self._ymax, p.y)


_OPTIONSPEC = (
    inkext.ExtOption('--scale', '-s', type='docunits', default=5.0, help='Output scale.'),
    inkext.ExtOption('--rotate', '-r', type='degrees', default=0.0, help='Rotation.'),
    inkext.ExtOption('--symmetry', '-S', type='int', default=5, help='Degrees of symmetry.'),
    inkext.ExtOption('--numlines', '-n', type='int', default=30, help='Number of lines.'),
    inkext.ExtOption('--offset-x', type='docunits', default=0.0, help='X offset'),
    inkext.ExtOption('--offset-y', type='docunits', default=0.0, help='Y offset'),
    inkext.ExtOption('--salt-x', type='float', default=0.31416, help='X offset salt'),
    inkext.ExtOption('--salt-y', type='float', default=0.64159, help='Y offset salt'),
    inkext.ExtOption('--epsilon', type='docunits', default=0.00001, help='Epsilon'),

    inkext.ExtOption('--segment-draw', type='inkbool', default=False, help='Draw segments.'),
    inkext.ExtOption('--segtype-skinny', '-M', type='int', default=0, help='Midpoint type for skinny diamonds.'),
    inkext.ExtOption('--segtype-fat', '-N', type='int', default=0, help='Midpoint type for fat diamonds.'),
    inkext.ExtOption('--skinnyfat-ratio', type='float', default=0.5, help='Skinny/fat ratio'),
    inkext.ExtOption('--segment-ratio', type='float', default=0.5, help='Segment ratio'),
    inkext.ExtOption('--segment-scale', type='float', default=1.0, help='Segment scale.'),
    inkext.ExtOption('--segment-split-cross', type='inkbool', default=False, help='Split crossed segments.'),
#     inkext.ExtOption('--segment-stroke', default='#000000', help='Segment CSS stroke color.'),
#     inkext.ExtOption('--segment-width', default='.1in', help='Segment CSS stroke width.'),
    inkext.ExtOption('--segment-sort', type='int', default=0, help='Sort segments by.'),

    inkext.ExtOption('--segpath-draw', type='inkbool', default=False, help='Draw segment paths.'),
    inkext.ExtOption('--segpath-closed', type='inkbool', default=False, help='Draw closed polygons only.'),
    inkext.ExtOption('--segpath-fillclosed', type='inkbool', default=False, help='Fill closed polygons.'),
    inkext.ExtOption('--segpath-min-segments', '-m', type='int', default=1, help='Min segments in path.'),
#     inkext.ExtOption('--segpath-stroke', default='#000000', help='Segment CSS stroke color.'),
#     inkext.ExtOption('--segpath-width', default='.1in', help='Segment CSS stroke width.'),

    inkext.ExtOption('--polygon-draw', type='inkbool', default=True, help='Draw polygons.'),
    inkext.ExtOption('--polygon-mult', type='int', default=0, help='Number of concentric polygons.'),
    inkext.ExtOption('--min-rhombus-width', type='docunits', default=0.0, help='Minimum rhombus width.'),
    inkext.ExtOption('--polygon-mult-spacing', type='docunits', default=0.0, help='Concentric polygon spacing.'),
    inkext.ExtOption('--polygon-fill', '-f', type='inkbool', default=False, help='Fill polygons.'),
#     inkext.ExtOption('--polygon-colorfill', type='inkbool', default=False, help='Use color fill.'),
    inkext.ExtOption('--polygon-zfill', '-z', type='inkbool', default=True, help='Fill color according to polygon type.'),
    inkext.ExtOption('--polygon-stroke', default='#f03030', help='Polygon CSS stroke color.'),
    inkext.ExtOption('--polygon-fill-lut', default='gray10', help='Fill color LUT'),
    inkext.ExtOption('--polygon-fill-lut-offset', type='int', default=0, help='LUT offset'),
#     inkext.ExtOption('--polygon-stroke-width', default='.2pt', help='Polygon CSS stroke width.'),
    inkext.ExtOption('--polygon-sort', type='int', default=0, help='Sort polygons by.'),

    inkext.ExtOption('--ellipse-draw', type='inkbool', default=False, help='Draw ellipses.'),
    inkext.ExtOption('--ellipse-cull', type='inkbool', default=False, help='Cull eccentric ellipses.'),
    inkext.ExtOption('--ellipse-min-radius', type='docunits', default=1.0, help='Ellipse min radius.'),
    inkext.ExtOption('--ellipse-inset', type='docunits', default=0, help='Ellipse inset.'),

    inkext.ExtOption('--polyseg-draw', type='inkbool', default=True, help='Draw polygon segments.'),
    inkext.ExtOption('--polyseg-scale', type='float', default=1.0, help='Polyseg scale.'),
    inkext.ExtOption('--polyseg-stroke', default='#000000', help='Polyseg CSS stroke color.'),
    inkext.ExtOption('--polyseg-stroke-width', default='.1in', help='Polyseg CSS stroke width.'),
    inkext.ExtOption('--polyseg-lut', default='none', help='Color set.'),
    inkext.ExtOption('--polyseg-layer-per-color', type='inkbool', default=False, help='Layer per color.'),
    inkext.ExtOption('--polyseg-clip-to-margins', type='inkbool', default=True, help='Clip polyseg to margins.'),

    inkext.ExtOption('--clip-to-doc', type='inkbool', default=True, help='Clip to document.'),
    inkext.ExtOption('--clip-to-circle', type='inkbool', default=False, help='Circular clip region.'),
    inkext.ExtOption('--clip-to-margins', '-C', type='inkbool', default=True, help='Clip to document margins.'),
    inkext.ExtOption('--clip-offset-center', type='inkbool', default=False, help='Offset center to clip region.'),
    inkext.ExtOption('--clip-recenter', type='inkbool', default=False, help='Re-center bounding box to clip region.'),

    inkext.ExtOption('--margin-left', type='docunits', default=0.0, help='Left margin'),
    inkext.ExtOption('--margin-right', type='docunits', default=0.0, help='Right margin'),
    inkext.ExtOption('--margin-top', type='docunits', default=0.0, help='Top margin'),
    inkext.ExtOption('--margin-bottom', type='docunits', default=0.0, help='Bottom margin'),

    inkext.ExtOption('--margin-draw', type='inkbool', default=False, help='Draw margins.'),
    inkext.ExtOption('--frame-draw', type='inkbool', default=False, help='Draw frame.'),

    inkext.ExtOption('--frame-width', type='docunits', default=0.0, help='Frame width'),
    inkext.ExtOption('--frame-height', type='docunits', default=0.0, help='Frame height'),
    inkext.ExtOption('--frame-thickness', type='docunits', default=1.0, help='Frame thickness'),

    inkext.ExtOption('--project-sphere', type='inkbool', default=False, help='Project on to sphere.'),
    inkext.ExtOption('--project-invert', type='inkbool', default=False, help='Invert projection.'),
    inkext.ExtOption('--project-radius-useclip', type='inkbool', default=False, help='Use clipping circle for radius.'),
    inkext.ExtOption('--project-radius', type='docunits', default=0.0, help='Projection radius.'),
    inkext.ExtOption('--blowup-scale', type='float', default=1.0, help='Blow up scale.'),


    inkext.ExtOption('--create-info-layer', type='inkbool', default=False, help='Create info layer'),
    inkext.ExtOption('--create-culledrhombus-layer', type='inkbool', default=False, help='Create culled rhombus layer'),
)

if __name__ == '__main__':
    plugin = QuasiExtension()
    plugin.main(_OPTIONSPEC)
