#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
Some handy polygon tools such as convex hull, area, and centroid
calculations.

====

Some references:
http://paulbourke.net/geometry/
http://geomalgorithms.com/index.html
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import sys
# import logging
# logger = logging.getLogger(__name__)

from . import const
from . import box

from .point import P
from .line import Line

# print('importing polygon')
# def dummy():
#     print('dummy')


TURN_LEFT, TURN_RIGHT, TURN_NONE = (1, -1, 0)

def turn(p, q, r):
    """Returns -1, 0, 1 if p,q,r forms a right, straight, or left turn.

    :param p: Point from which initial direction is determined.
        A 2-tuple (x, y) point.
    :param q: Point from which turn is determined. A 2-tuple (x, y) point.
    :param r: End point which determines turn direction. A 2-tuple (x, y) point.
    """
    return cmp((q[0] - p[0])*(r[1] - p[1]) - (r[0] - p[0])*(q[1] - p[1]), 0)

def convex_hull(points):
    """Returns points on convex hull of an array of points in CCW order.

    Uses the Graham Scan algorithm.

    :param points: a list of 2-tuple (x, y) points.
    :return: The convex hull as a list of 2-tuple (x, y) points.
    """
    points = sorted(points)
    lh = reduce(_keep_left, points, [])
    uh = reduce(_keep_left, reversed(points), [])
#    lh.extend(uh[i] for i in range(1, len(uh) - 1))
    lh.extend(uh[1:-1])
    return lh

def _keep_left(hull, r):
    while len(hull) > 1 and turn(hull[-2], hull[-1], r) != TURN_LEFT:
        hull.pop()
    if not len(hull) or hull[-1] != r:
        hull.append(P(r))
    return hull


#==============================================================================
# Chan's Convex Hull O(n log h) - Tom Switzer <thomas.switzer@gmail.com>
# See http://tomswitzer.net/2010/12/2d-convex-hulls-chans-algorithm/
#==============================================================================
def convex_hull_chan(points):
    """Returns the points on the convex hull of points in CCW order.

    Uses Chan's algorithm. May be faster than Graham scan on
    large point collections.

    See http://tomswitzer.net/2010/12/2d-convex-hulls-chans-algorithm/

    :param points: a list of 2-tuple (x, y) points.
    :return: The convex hull as a list of 2-tuple (x, y) points.
    """
#    for m in (1 << (1 << t) for t in range(len(points))):
    for m in ((1 << t) for t in range(len(points))):
        hulls = [convex_hull(points[i:i + m])
                 for i in range(0, len(points), m)]
        hull = [_min_hull_pt_pair(hulls)]
        for unused in range(m):
            p = _next_hull_pt_pair(hulls, hull[-1])
            if p == hull[0]:
                return [hulls[h][i] for h, i in hull]
            hull.append(P(p))
    return hull

def _rtangent(hull, p):
    """Return the index of the point in hull that the right tangent line from p
    to hull touches.
    """
    l, r = 0, len(hull)
    l_prev = turn(p, hull[0], hull[-1])
    l_next = turn(p, hull[0], hull[(l + 1) % r])
    while l < r:
        c = (l + r) / 2
        c_prev = turn(p, hull[c], hull[(c - 1) % len(hull)])
        c_next = turn(p, hull[c], hull[(c + 1) % len(hull)])
        c_side = turn(p, hull[l], hull[c])
        if c_prev != TURN_RIGHT and c_next != TURN_RIGHT:
            return c
        elif c_side == TURN_LEFT and (l_next == TURN_RIGHT or
                                      l_prev == l_next) or \
                c_side == TURN_RIGHT and c_prev == TURN_RIGHT:
            r = c               # Tangent touches left chain
        else:
            l = c + 1           # Tangent touches right chain
            l_prev = -c_next    # Switch sides
            l_next = turn(p, hull[l], hull[(l + 1) % len(hull)])
    return l

def _min_hull_pt_pair(hulls):
    """Returns the hull, point index pair that is minimal."""
    h, p = 0, 0
    for i in range(len(hulls)):
        j = min(range(len(hulls[i])), key=lambda j: hulls[i][j])
        if hulls[i][j] < hulls[h][p]:
            h, p = i, j
    return (h, p)

def _dist2(p1, p2):
    """Euclidean distance squared between two points."""
    a = p1[0] - p2[0]
    b = p1[1] - p2[1]
    return (a * a) + (b * b)

def _next_hull_pt_pair(hulls, pair):
    """
    Returns the (hull, point) index pair of the next point in the convex
    hull.
    """
    p = hulls[pair[0]][pair[1]]
    nextpair = (pair[0], (pair[1] + 1) % len(hulls[pair[0]]))
    for h in (i for i in range(len(hulls)) if i != pair[0]):
        s = _rtangent(hulls[h], p)
        q, r = hulls[nextpair[0]][nextpair[1]], hulls[h][s]
        t = turn(p, q, r)
        if t == TURN_RIGHT or t == TURN_NONE and _dist2(p,r) > _dist2(p,q):
            nextpair = (h, s)
    return nextpair

def bounding_box(points):
    """Simple bounding box of a collection of points.

    :param points: an iterable collection of point 2-tuples (x,y).
    """
    xmin = sys.float_info.max
    ymin = sys.float_info.max
    xmax = sys.float_info.min
    ymax = sys.float_info.min
    for p in points:
        x, y = p
        xmin = min(xmin, x)
        ymin = min(ymin, y)
        xmax = max(xmax, x)
        ymax = max(ymax, y)
    return box.Box(P(xmin, ymin), P(xmax, ymax))

#==============================================================================
# Area and centroid calculations for non self-intersecting closed polygons.
# See http://paulbourke.net/geometry/polygonmesh/
#==============================================================================

def area(vertices):
    """Return the area of a simple polygon.

    :param vertices: the polygon vertices. A list of 2-tuple (x, y) points.
    :return: The area of the polygon. The area will be negative if the
        vertices are ordered clockwise.
    """
    area = 0.0
    for n in range(-1, len(vertices) - 1):
        p2 = vertices[n]
        p1 = vertices[n+1]
        # Accumulate the cross product of each pair of vertices
        area += ((p1[0] * p2[1]) - (p2[0] * p1[1]))
    return area / 2

def centroid(vertices):
    """Return the centroid of a simple polygon.

    See http://paulbourke.net/geometry/polygonmesh/

    :param vertices: The polygon vertices. A list of 2-tuple (x, y) points.
    :return: The centroid point as a 2-tuple (x, y)
    """
    num_vertices = len(vertices)
    # Handle degenerate cases for point and single segment
    if num_vertices == 1:
        # if it's just one point return the same point
        return vertices[0]
    if num_vertices == 2:
        # if it's a single segment just return the midpoint
        return Line(vertices[0], vertices[1]).midpoint()
    x = 0.0
    y = 0.0
    area = 0.0
    for n in range(-1, num_vertices-1):
        p2 = vertices[n]
        p1 = vertices[n+1]
        cross = ((p1[0] * p2[1]) - (p2[0] * p1[1]))
        area += cross
        x += (p1[0] + p2[0]) * cross
        y += (p1[1] + p2[1]) * cross
    t = area * 3
    return P(x/t, y/t)


#==============================================================================
#Portions of this code (point in polygon test) are derived from:
#http://www.ecse.rpi.edu/Homepages/wrf/Research/Short_Notes/pnpoly.html
#and uses the following license:
#Copyright (c) 1970-2003, Wm. Randolph Franklin
#
#Permission is hereby granted, free of charge, to any person obtaining a copy of
#this software and associated documentation files (the "Software"), to deal in
#the Software without restriction, including without limitation the rights to
#use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
#of the Software, and to permit persons to whom the Software is furnished to do
#so, subject to the following conditions:
#Redistributions of source code must retain the above copyright notice,
#this list of conditions and the following disclaimers.
#Redistributions in binary form must reproduce the above copyright notice in the
#documentation and/or other materials provided with the distribution.
#The name of W. Randolph Franklin may not be used to endorse or promote products
#derived from this Software without specific prior written permission.
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.
#==============================================================================

def point_inside(vertices, p):
    """Return True if point `p` is inside the polygon defined by `vertices`.

    See: http://www.ecse.rpi.edu/Homepages/wrf/Research/Short_Notes/pnpoly.html
    Also: http://paulbourke.net/geometry/polygonmesh/
    Also: http://geomalgorithms.com/a03-_inclusion.html


    :param vertices: polygon vertices. A list of 2-tuple (x, y) points.
    :param p: Point to test.
    :return: True if the point lies inside the polygon, else False.
    """
    is_inside = False
    x, y = p
    j = -1
    for i in range(len(vertices)):
        # endpoints of each polygon segment
#        p1 = vertices[i]
#        p2 = vertices[j]
#        # This is a tricky conditional - see W. R. Franklin's web page
#        if ((p1.y > p.y) != (p2.y > p.y)) and \
#           p.x < (((p2.x - p1.x) * (p.y - p1.y) / (p2.y - p1.y)) + p1.x):
#        if (p1[1] > y) != (p2[1] > y) and \
#           x < (((p2[0] - p1[0]) * (y - p1[1]) / (p2[1] - p1[1])) + p1[0]):
#            is_inside = not is_inside
        x1, y1 = vertices[i]
        x2, y2 = vertices[j]
        # This is a tricky conditional - see W. R. Franklin's web page
        if (y1 > y) != (y2 > y) and x < ((x2 - x1) * (y - y1) / (y2 - y1)) + x1:
            is_inside = not is_inside
        j = i
    return is_inside


def intersect_line(vertices, line):
    """Compute the intersection(s) of a polygon and a line segment.

    :param vertices: the polygon vertices. An iterable of 2-tuple (x, y) points.
    :param line: a line possibly intersecting the polygon. A 2-tuple of line
        end points, each a 2-tuple ``((x1, y1), (x2, y2))``.
    :return: a list of one or more line segments that intersect the polygon
        or that lie completely within the polygon. Returns an empty list
        if there are no intersections.
    """
    if not isinstance(line, Line):
        line = Line(line)
    # automatically close the polygon
    start = 0 if vertices[0] == vertices[-1] else -1
    # Find all the intersections of the line segment with the polygon
    intersections = []
    for i in range(start, len(vertices) - 1):
        line2 = Line(vertices[i], vertices[i+1])
        # Find the intersection unit distance (mu) from the line start point
        mu = line.intersection_mu(line2, segment=True)
        if mu is not None:
            intersections.append(mu)

    num_intersections = len(intersections)
    p1_inside = point_inside(vertices, line[0])
    p2_inside = point_inside(vertices, line[1])
    if num_intersections == 0 and p1_inside and p2_inside:
        # Line segment is completely contained by the polygon
        return (line,)
    segments = []
    if num_intersections > 0:
        # Sort intersections in mu order
        intersections.sort()
        i = 0
        # Determine the starting point
        if p1_inside:
            p1 = line[0]
        elif p2_inside:
            p1 = line[1]
            intersections.reverse()
        else:
            p1 = line.point_at(intersections[0])
            i = 1
        while i < num_intersections:
            p2 = line.point_at(intersections[i])
            if p1 != p2: # cull degenerate lines - may not be necessary...
                segments.append(Line(p1, p2))
            if (i + 1) == num_intersections:
                break
            p1 = line.point_at(intersections[i+1])
            i += 2
    return segments

def is_closed(vertices):
    """Return True if the polygon is closed. I.e. if the
    first vertice matches the last vertice."""
    x1, y1 = vertices[0]
    xn, yn = vertices[-1]
    return const.float_eq(x1, xn) and const.float_eq(y1, yn)


#class ClipPolygon(object):
#    """Clipping polygon."""
#
#    def __init__(self, vertices):
#        """
#        :param vertices: the polygon vertices.
#            An iterable of 2-tuple (x, y) points.
#        """
#        self.vertices = vertices
#
#    def point_inside(self, p):
#        """Return True if the point is inside this polygon."""
#        return point_inside(self.vertices, p)
#
#    def clip_line(self, line):
#        """Compute the intersection(s), if any, of this polygon
#        and a line segment.
#
#        :param line: the line to test for intersections.
#        :return: a list of one or more line segments that intersect the polygon
#            or that lie completely within the polygon. Returns None if there are
#            no intersections.
#        """
#        return intersect_line(self.vertices, line)
#

