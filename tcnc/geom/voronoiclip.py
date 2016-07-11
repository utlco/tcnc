#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import . import voronoi

from .point import P
from .line import Line
from . import polygon

def clip_voronoi_segments(self, diagram, clip_rect):
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
            a, b, c = edge.equation
            if b == 0:
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
        line = clip_rect.clip_line(Line(p1, p2))
        if line is not None:
            voronoi_segments.append(line)
    return voronoi_segments


def clip_voronoi_segments_poly(self, voronoi_segments, clip_polygon):
    """Clip voronoi segments to a polygon.

    Args:
        voronoi_segments:
    """
    voronoi_clipped_segments = []
    for segment in voronoi_segments:
        if clip_polygon is not None:
            cliplines = polygon.intersect_line(clip_polygon, segment)
            for line in cliplines:
                voronoi_clipped_segments.append(line)
    return voronoi_clipped_segments


def clipped_delaunay_segments(self, voronoi_diagram, clip_polygon):
    """
    """
    delaunay_segments = []
    for edge in voronoi_diagram.delaunay_edges:
        line = Line(edge.p1, edge.p2)
        if (clip_polygon is None
            or self._line_inside_hull(clip_polygon, line, allow_hull=True)):
            delaunay_segments.append(line)
    return delaunay_segments


def line_inside_hull(self, points, line, allow_hull=False):
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
            pp1 = P(points[i])
            pp2 = P(points[i-1])
            if Line(pp1, pp2) == line:
                return True
    if not polygon.point_inside(points, line.midpoint()):
        return False
    p1 = line.p1
    p2 = line.p2
    if not allow_hull:
        for i in range(len(points)):
            pp1 = P(points[i])
            pp2 = P(points[i-1])
            if Line(pp1, pp2) == line:
                return False
    for i in range(len(points)):
        pp1 = P(points[i])
        pp2 = P(points[i-1])
        if p1 == pp1 or p1 == pp2 or p2 == pp1 or p2 == pp2:
            return True
    return (polygon.point_inside(points, p1)
            or polygon.point_inside(points, p2))

