#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
An Inkscape extension to create lines between two polylines.

====
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import random
import gettext
import logging

import geom

from geom import polygon

from svg import geomsvg
from inkscape import inkext

__version__ = "0.2"

_ = gettext.gettext
logger = logging.getLogger(__name__)


class PipeLines(inkext.InkscapeExtension):
    """
    """
    OPTIONSPEC = (
        inkext.ExtOption('--epsilon', type='docunits', default=0.00001,
                         help='Epsilon'),
        inkext.ExtOption('--pipeline-count', type='int', default=3,
                         help='Line count'),
        inkext.ExtOption('--pipeline-fillet', type='inkbool', default=False,
                         help='Fillet lines'),
        inkext.ExtOption('--pipeline-fillet-radius', type='float', default=0,
                         help='Fillet radius.'),
        inkext.ExtOption('--pipeline-maxspacing', type='float', default=0,
                         help='Max spacing'),
        inkext.ExtOption('--pipeline-stroke', default='#000000',
                         help='Line CSS stroke color'),
        inkext.ExtOption('--pipeline-stroke-width', default='3px',
                         help='Line CSS stroke width'),
    )

    _styles = {
        'dot':
            'fill:%s;stroke-width:1px;stroke:#000000;',
        'pipeline':
            'fill:none;stroke-opacity:1.0;stroke-linejoin:round;'
            'stroke-width:${pipeline_stroke_width};stroke:${pipeline_stroke};',
#        'segment':
#            'fill:none;stroke-opacity:1.0;stroke-linejoin:round;'
#            'stroke-width:${segment_stroke_width};stroke:${segment_stroke};',
#        'segment1':
#            'fill:none;stroke-opacity:1.0;stroke-linejoin:round;'
#            'stroke-width:${segment1_stroke_width};stroke:${segment1_stroke};',
    }

    _style_defaults = {
        'pipeline_stroke_width': '3pt',
        'pipeline_stroke': '#505050',
#        'segment_stroke_width': '3pt',
#        'segment_stroke': '#00a000',
#        'segment1_stroke_width': '3pt',
#        'segment1_stroke': '#f00000',
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

        # Path list should only have two sort of parallel paths
        if len(path_list) != 2:
            self.errormsg(_('Please select two polylines'))
            exit(1)

        layer = self.svg.create_layer('q_polylines', incr_suffix=True)
#        seglayer = self.svg.create_layer('q_segments', incr_suffix=True)
        segments = self._get_segments(path_list[0], path_list[1])

        if segments:
            self._draw_segments(segments)
            polylines = self._get_polylines(path_list[0], path_list[1], segments)
            if polylines:
                self._draw_polylines(polylines, layer)

    def _get_segments(self, path1, path2):
        """ This is ridiculously non-optimal, but who cares...
        """
        bbox = polygon.bounding_box([p1 for p1, _p2 in path1]
                                    + [p1 for p1, _p2 in path2])
        # Make sure both paths are going more or less in the same direction
        # by checking if the distance between the starting points is less
        # than the distance between one path starting point and the other
        # path ending point.
        d1 = path1[0].p1.distance(path2[0].p1)
        d2 = path1[0].p1.distance(path2[-1].p2)
        if d1 > d2:
            geom.util.reverse_path(path2)
        rays = [geom.Line(path1[0].p1, path2[0].p1)]
        rayside = path1[0].which_side(path2[0].p1)
        p0 = path1[0].p1
        for p1, p2 in path1[1:]:
            if abs(p1.angle2(p0, p2)) > geom.const.EPSILON:
                # The angle bisector at each vertex
                bisector = geom.Line(p1, p1.bisector(p0, p2))
                # Make sure it's pointing the right way
                if geom.Line(p0, p1).which_side(bisector.p2) != rayside:
                    bisector = bisector.flipped()
#                geom.debug.draw_line(bisector, width=11)
                bisector = bisector.extend(bbox.diagonal())
                # See if it intersects a segment on the other path
                lx = self._linex_segment(bisector, path1, path2)
                if lx is not None:
                    rays.append(lx)
            p0 = p1
        # Do the same for the other path
        rayside = -rayside
        p0 = path2[0].p1
        for p1, p2 in path2[1:]:
            bisector = geom.Line(p1, p1.bisector(p0, p2))
            if geom.Line(p0, p1).which_side(bisector.p2) != rayside:
                bisector = bisector.flipped()
#            geom.debug.draw_line(bisector, width=11)
            bisector = bisector.extend(bbox.diagonal())
            lx = self._linex_segment(bisector, path2, path1)
            if lx is not None:
                rays.append(lx.reversed())
            p0 = p1
        # Last line joining the path endpoints
        rays.append(geom.Line(path1[-1].p2, path2[-1].p2))
        # Sort the segment endpoints on each path by distance from first
        # path endpoint. Then connect the sorted segment endpoints.
        p1list = [seg.p1 for seg in rays]
        p2list = [seg.p2 for seg in rays]
        p1list.sort(key=lambda p: self._pline_distance(p, path1))
        p2list.sort(key=lambda p: self._pline_distance(p, path2))
        rays = [geom.Line(p1, p2) for p1, p2 in zip(p1list, p2list)]
        # Sort the segments by distance on first path
#        rays.sort(key=lambda seg: self._pline_distance(seg.p1, path1))
#        for i, ray in enumerate(rays):
#            logger.debug('ray[%d]: %.3f, %.3f', i, ray.length(), self._pline_distance(ray.p1, path1))
#            geom.debug.draw_point(ray.p1, radius=7, color='#ffff00')
#        geom.debug.draw_point(rays[8].p1, radius=7, color='#ffff00')
#        geom.debug.draw_line(path1[5], color='#ffff00', width=7)
#        if path1[5].point_on_line(rays[8].p1):
#            logger.debug('yep')
#        logger.debug('d: %.3f', self._pline_distance(rays[25].p1, path1))
#        return self._elim_crossings(rays, path1, path2)
        return rays

    def _num_polylines(self, segments):
        """ Get the number of polylines to draw
        """
        if self.options.pipeline_maxspacing > 0:
            maxlen = 0
            for seg in segments:
                seglen = seg.length()
                if seglen > maxlen:
                    maxlen = seglen
            return int(round(maxlen / self.options.pipeline_maxspacing))
        else:
            return self.options.pipeline_count

    def _get_polylines(self, path1, path2, segments):
        """
        """
        count = self._num_polylines(segments)
        polylines = []
        for seg in segments:
            seglen = seg.length()
            mu = ((seglen / (count + 1)) / seglen)
            for n in range(count):
                mu_i = mu * (n + 1)
                p = seg.point_at(mu_i)
                if len(polylines) < (n + 1):
                    polylines.append([])
                polylines[n].append(p)
#        for i in range(count):
#            for seg in segments:
#                seglen = seg.length()
#                mu = ((seglen / (count + 1)) / seglen) * (i + 1)
#                p = seg.point_at(mu)
#                polylines[i].append(p)
        return polylines

    def _linex_segment(self, ray, path1, path2):
        """ Get the segment from the starting point of the ray
        (on the first path) to its
        intersection with the second path.
        """
        ilines = []
#        d1 = self._pline_distance(ray.p1, path1)
#        logger.debug('ray d1: %.3f', d1)
        for seg in path2:
            px = ray.intersection(seg, segment=True)
            if px is not None:
#                geom.debug.draw_point(px)
                lx = geom.Line(ray.p1, px)
#                geom.debug.draw_line(lx, color='#ff00ff')
                ilines.append(lx)
        # If multiple intersections, return the shortest.
        if ilines:
#            logger.debug('intersects: %d', len(ilines))
            ilines.sort(key=lambda l: l.length())
#            ilines.sort(key=lambda lx: abs(d1 - self._pline_distance(lx.p2, path2)))
            for lx in ilines:
                if lx.length() > 0.001:
                    break
#            logger.debug('l: %f', lx.length())
#            lx = ilines[0]
#            geom.debug.draw_line(lx, color='#ff00ff', width=15, opacity=.5)
#            d = abs(d1 - self._pline_distance(lx.p2, path2))
#            logger.debug('lx d: %.3f', d)
            return lx
        return None

    def _draw_segments(self, segments):
        """ Draw guide segments on debug layer
        """
        # Draw a point at the starting path endpoint.
        geom.debug.draw_point(segments[0].p1, radius=11, color='#00ff00')
        for seg in segments:
            geom.debug.draw_line(seg, color='#0080ff')

    def _draw_polylines(self, polylines, layer):
        """
        """
        for pline in polylines:
            self.svg.create_polygon(pline, close_polygon=False,
                                    style=self._styles['pipeline'],
                                    parent=layer)

    def _pline_distance(self, p, path):
        """ Distance from the starting point of a polyline to a point
        on the same polyline.
        """
        d = 0.0
        for seg in path:
            if seg.point_on_line(p, segment=True):
#                geom.debug.draw_point(p, radius=11, color='#ff0000')
#                geom.debug.draw_line(seg, color='#ffff00', width=7)
                d += seg.p1.distance(p)
#                logger.debug('d: %.4f', d)
                return d
            d += seg.length()
#        logger.debug('wtf?')
#        geom.debug.draw_point(p, radius=11, color='#ff0000')
#        geom.debug.draw_line(seg, color='#ffff00', width=7)
#        logger.debug('p: (%f, %f)', p.x, p.y)
#        geom.debug.draw_line(path[3], color='#ffff00', width=7)
#        logger.debug('seg: (%f, %f) (%f, %f)', path[3].p1.x, path[3].p1.y, path[3].p2.x, path[3].p2.y)
#        logger.debug('seg: (%f, %f) (%f, %f)', path[4].p1.x, path[4].p1.y, path[4].p2.x, path[4].p2.y)
        return d

#    def _elim_crossings(self, segments, path1, path2):
#        """ Deal with intersecting segments
#        """
#        prev_seg = segments[0]
#        segments2 = [prev_seg]
#        p1x = []
#        p2x = []
#        for seg in segments[1:]:
#            px = prev_seg.intersection(seg, segment=True)
#            if px is not None:
#                if not p1x:
#                    p1x.append(prev_seg.p1)
#                    p2x.append(prev_seg.p2)
#                    segments2.pop()
#                p1x.append(seg.p1)
#                p2x.append(seg.p2)
##                if prev_seg.p1 == seg.p1:
##                    d1 = self._pline_distance(prev_seg.p2, path2)
##                    d2 = self._pline_distance(seg.p2, path2)
##                    if d1 > d2:
##                        segments2.insert(-1, seg)
##                    else:
##                        segments2.append(seg)
##                elif prev_seg.p2 == seg.p2:
##                    d1 = self._pline_distance(prev_seg.p1, path1)
##                    d2 = self._pline_distance(seg.p1, path1)
##                    if d1 > d2:
##                        segments2.insert(-1, seg)
##                    else:
##                        segments2.append(seg)
##                else:
##                    if not p1x:
##                        p1x.append(prev_seg.p1)
##                        p2x.append(prev_seg.p2)
##                        segments2.pop()
##                    p1x.append(seg.p1)
##                    p2x.append(seg.p2)
#            else:
#                if p1x:
##                    for p1, p2 in zip(p1x, p2x):
##                        geom.debug.draw_line(geom.Line(p1, p2), color='#ff0000')
##                    p = reduce(lambda x, y: x if x == y else None, p1x)
##                    if p != p1x[0]:
##                        p2x.reverse()
#                    p1x.sort(key=lambda p: self._pline_distance(p, path1))
#                    p2x.sort(key=lambda p: self._pline_distance(p, path2))
#                    for p1, p2 in zip(p1x, p2x):
#                        segments2.append(geom.Line(p1, p2))
#                    p1x = []
#                    p2x = []
#                segments2.append(seg)
#            prev_seg = seg
#        return segments2


if __name__ == '__main__':
    PipeLines().main(optionspec=PipeLines.OPTIONSPEC)
