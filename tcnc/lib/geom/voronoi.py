"""Voronoi diagram / Delaunay triangulation.

Compute a Voronoi diagram and optional Delaunay triangulation for a set of
2D input points.

Based on Steve Fortune's original code:
    http://ect.bell-labs.com/who/sjf/

Derek Bradley's fixes for memory leaks:
    http://zurich.disneyresearch.com/derekbradley/voronoi.html

Shane O'Sullivan's updates:
    http://mapviewer.skynet.ie/voronoi.html

Translated to Python by Bill Simons September, 2005:
    (not sure where this original translation can be found anymore)

Nicely refactored version by Manfred Moitzi at:
    https://bitbucket.org/mozman/geoalg

This version was based on the Bill Simons version
and refactored with some of Moitzi's cleanups.

Derived from code bearing the following notice::

    The author of this software is Steven Fortune. Copyright (c) 1994 by AT&T
    Bell Laboratories.

    Permission to use, copy, modify, and distribute this software for any
    purpose without fee is hereby granted, provided that this entire notice
    is included in all copies of any software which is or includes a copy
    or modification of this software and in all copies of the supporting
    documentation for such software.
    THIS SOFTWARE IS BEING PROVIDED "AS IS", WITHOUT ANY EXPRESS OR IMPLIED
    WARRANTY.  IN PARTICULAR, NEITHER THE AUTHORS NOR AT&T MAKE ANY
    REPRESENTATION OR WARRANTY OF ANY KIND CONCERNING THE MERCHANTABILITY
    OF THIS SOFTWARE OR ITS FITNESS FOR ANY PARTICULAR PURPOSE.

Comments were incorporated from Shane O'Sullivan's translation of the
original code into C++:

    http://mapviewer.skynet.ie/voronoi.html

This module has no dependencies besides standard Python libraries.

====
"""
# pylint: disable=empty-docstring, too-few-public-methods
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import math
import sys
import random


#: Tolerance for floating point comparisons
EPSILON = 1e-9

class VoronoiEdge(tuple):
    """A Voronoi edge. The dual of a corresponding
    This is a line segment that bisects a line
    between nearest neighbor sites.

    If one end point of the edge is None it means
    the line extends to infinity. If the first
    end point is None the edge extends to the left.
    If the second end point is None the edge extends
    to the right.
    """
    def __new__(cls, p1, p2, line, delaunay_edge=None):
        """"""
        if delaunay_edge is None:
            return tuple.__new__(VoronoiEdge, (p1, p2, line))
        else:
            return tuple.__new__(VoronoiEdge, (p1, p2, line, delaunay_edge))

    @property
    def p1(self):
        """First point of edge segment."""
        return self[0]

    @property
    def p2(self):
        """Second point of edge segment."""
        return self[1]

    @property
    def equation(self):
        """The line equation for this segment
        in the form `a*x + b*y = c`
        as a 3-tuple (a, b, c)
        """
        return self[2]

    @property
    def delaunay_edge(self):
        """The dual of this Voronoi edge.
        """
        if len(self) < 4:
            return None
        else:
            return self[3]


class DelaunayEdge(tuple):
    """A Delaunay edge. The dual of a corresponding
    Voronoi segment that bisects this Delaunay segment.
    This is a line segment between nearest neighbor sites.
    """
    def __new__(cls, p1, p2):
        """"""
        return tuple.__new__(DelaunayEdge, (p1, p2))
    @property
    def p1(self):
        """First point of edge segment."""
        return self[0]

    @property
    def p2(self):
        """Second point of edge segment."""
        return self[1]
#
#     @property
#     def voronoi_edge(self):
#         """The dual of this Delaunay edge.
#         The Voronoi edge bisects this edge.
#         """
#         return self[3]


class DelaunayTriangle(tuple):
    """A Delaunay triangle.
    This a 3-tuple of 2-tuple (x, y) points.
    """
    def __new__(cls, p1, p2, p3):
        """"""
        return tuple.__new__(DelaunayTriangle, (p1, p2, p3))

    @property
    def p1(self):
        """First point of triangle."""
        return self[0]

    @property
    def p2(self):
        """Second point of triangle."""
        return self[1]

    @property
    def p3(self):
        """Third point of triangle."""
        return self[1]


class VoronoiDiagram(object):
    """Voronoi diagram and Delaunay triangulation.
    """
    def __init__(self, input_points, do_delaunay=False, jiggle_points=False):
        """
        Args:
            input_points: An indexable collection of points as (x, y) 2-tuples
            do_delaunay: True if Delaunay edges and triangles are
                to be generated. Default is False.
            jiggle_points: Jiggle the input points by a small random
                distance to mitigate problems caused by degenerate
                point sets (such as collinear or coincident points).
                Default is False.
        """
        self._do_delaunay = do_delaunay
        self._vertices = []
        self._lines = []
        self._edges = []
        self._triangles = []
        self._delaunay_edges = []
        if len(input_points) > 4:
            if jiggle_points:
                input_points = [jiggle(p) for p in input_points]
            self._compute_voronoi(input_points)

    @property
    def vertices(self):
        """List of the Voronoi diagram vertices as 2-tuple (x, y) coordinates.
        """
        return self._vertices

#     @property
#     def lines(self):
#         """List of Voronoi edges as line equations.
#         A line is a 3-tuple (a, b, c) for the
#         line equation of the form `a*x + b*y = c`
#         """
#         return self._lines

    @property
    def edges(self):
        """List of VoronoiEdges.
        """
        return self._edges

    @property
    def triangles(self):
        """List of DelaunayTriangles.
        """
        return self._triangles

    @property
    def delaunay_edges(self):
        """List of DelaunayEdges.
        """
        return self._delaunay_edges

    def _add_vertex(self, site):
        site.sitenum = len(self._vertices)
        self._vertices.append((site.x, site.y))

    def _add_triangle(self, p1, p2, p3):
        self._triangles.append(DelaunayTriangle(p1, p2, p3))

    def _add_bisector(self, edge):
        edge.edgenum = len(self._lines)
        self._lines.append((edge.a, edge.b, edge.c))
        if self._do_delaunay:
            segment = DelaunayEdge((edge.dsegment[0].x, edge.dsegment[0].y),
                                   (edge.dsegment[1].x, edge.dsegment[1].y))
            self._delaunay_edges.append(segment)

    def _add_edge(self, edge):
        p1 = None
        p2 = None
        delaunay_edge = None
        if edge.endpoints[_Edge.LEFT] is not None:
            sitenum_left = edge.endpoints[_Edge.LEFT].sitenum
            p1 = self._vertices[sitenum_left]
        if edge.endpoints[_Edge.RIGHT] is not None:
            sitenum_right = edge.endpoints[_Edge.RIGHT].sitenum
            p2 = self._vertices[sitenum_right]
        if self._do_delaunay:
            delaunay_edge = self._delaunay_edges[edge.edgenum]
        voronoi_edge = VoronoiEdge(p1, p2, self._lines[edge.edgenum],
                                   delaunay_edge)
        self._edges.append(voronoi_edge)

    def _compute_voronoi(self, input_points):
        """Create a Voronoi diagram.

        Args:
            input_points: A list of points as (x, y) 2-tuples
        """
        sites = _SiteList(input_points)
        nsites = len(sites)
        edges = _EdgeList(sites.xmin, sites.xmax, nsites)
        priority_queue = _PriorityQueue(sites.ymin, sites.ymax, nsites)
        itersites = iter(sites)

        bottomsite = itersites.next()
        newsite = itersites.next()
        min_point = _Site(sys.float_info.min, sys.float_info.min)

        while True:
            if not priority_queue.is_empty():
                min_point = priority_queue.get_min_point()
            if newsite and (priority_queue.is_empty() or newsite < min_point):
                self._handle_event1(priority_queue, edges, bottomsite, newsite)
                try:
                    newsite = itersites.next()
                except StopIteration:
                    newsite = None
            elif not priority_queue.is_empty():
                # intersection is smallest - this is a vector (circle) event
                self._handle_event2(input_points, priority_queue, edges,
                                    bottomsite)
            else:
                break

        halfedge = edges.leftend.right
        while halfedge is not edges.rightend:
            self._add_edge(halfedge.edge)
            halfedge = halfedge.right

    def _handle_event1(self, priority_queue, edges, bottomsite, newsite):
        # get first HalfEdge to the LEFT and RIGHT of the new site
        lbnd = edges.pop_leftbnd(newsite)
        rbnd = lbnd.right

        # if this halfedge has no edge, bot = bottom site
        # create a new edge that bisects
        bot = lbnd.right_site(bottomsite)
        edge = _Edge(bot, newsite)
        self._add_bisector(edge)

        # create a new HalfEdge, setting its orientation to LEFT and insert
        # this new bisector edge between the left and right vectors in
        # a linked list
        bisector = _HalfEdge(edge, _Edge.LEFT)
        edges.insert(lbnd, bisector)

        # if the new bisector intersects with thalfedge left edge,
        # remove the left edge's vertex, and put in the new one
        site = lbnd.intersect(bisector)
        if site is not None:
            priority_queue.delete(lbnd)
            priority_queue.insert(lbnd, site, newsite.distance(site))

        # create a new HalfEdge, setting its orientation to RIGHT
        # insert the new HalfEdge to the right of the original bisector
        lbnd = bisector
        bisector = _HalfEdge(edge, _Edge.RIGHT)
        edges.insert(lbnd, bisector)

        # if this new bisector intersects with the right HalfEdge
        site = bisector.intersect(rbnd)
        if site is not None:
            # push the HalfEdge into the ordered linked list
            # of vertices
            priority_queue.insert(bisector, site, newsite.distance(site))

    def _handle_event2(self, input_points, priority_queue, edges, bottomsite):
        # Pop the HalfEdge with the lowest vector off the ordered list
        # of vectors.
        # Get the HalfEdge to the left and right of the above HalfEdge
        # and also the HalfEdge to the right of the right HalfEdge
        lbnd = priority_queue.pop_min_halfedge()
        llbnd = lbnd.left
        rbnd = lbnd.right
        rrbnd = rbnd.right

        # get the Site to the left of the left HalfEdge and
        # to the right of the right HalfEdge which it bisects
        bot = lbnd.left_site(bottomsite)
        top = rbnd.right_site(bottomsite)
        orientation = _Edge.LEFT
        # If the site to the left of the event is higher than the Site
        # to the right of it, then swap the half edge orientation.
        if bot.y > top.y:
            bot, top = top, bot
            orientation = _Edge.RIGHT

        # Output the triple of sites (a Delaunay triangle)
        # stating that a circle goes through them
        if self._do_delaunay:
            mid = lbnd.right_site(bottomsite)
            self._add_triangle(input_points[bot.sitenum],
                               input_points[top.sitenum],
                               input_points[mid.sitenum])

        # Add the vertex that caused this event to the Voronoi diagram.
        vertex = lbnd.vertex
        self._add_vertex(vertex)
        # set the endpoint of the left and right HalfEdge to be
        # this vector.
        if lbnd.edge.set_endpoint(lbnd.orientation, vertex):
            self._add_edge(lbnd.edge)
        if rbnd.edge.set_endpoint(rbnd.orientation, vertex):
            self._add_edge(rbnd.edge)

        # delete the lowest HalfEdge, remove all vertex events to do with the
        # right HalfEdge and delete the right HalfEdge
        edges.delete(lbnd)
        priority_queue.delete(rbnd)
        edges.delete(rbnd)

        # Create an Edge (or line) that is between the two Sites.
        # This creates the formula of the line, and assigns
        # a line number to it
        edge = _Edge(bot, top)
        self._add_bisector(edge)

        # create a HalfEdge from the edge
        bisector = _HalfEdge(edge, orientation)

        # insert the new bisector to the right of the left HalfEdge
        # set one endpoint to the new edge to be the vector point
        # 'vertex'.
        # If the site to the left of this bisector is higher than
        # the right Site, then this endpoint is put in position 0;
        # otherwise in pos 1.
        edges.insert(llbnd, bisector)
        if edge.set_endpoint(_Edge.RIGHT - orientation, vertex):
            self._add_edge(edge)

        # if left HalfEdge and the new bisector don't intersect, then delete
        # the left HalfEdge, and reinsert it
        site = llbnd.intersect(bisector)
        if site is not None:
            priority_queue.delete(llbnd)
            priority_queue.insert(llbnd, site, bot.distance(site))

        # if right HalfEdge and the new bisector don't intersect,
        # then reinsert it
        site = bisector.intersect(rrbnd)
        if site is not None:
            priority_queue.insert(bisector, site, bot.distance(site))


class _Site(object):
    """"""
    def __init__(self, x, y, sitenum=0):
        self.x = x
        self.y = y
        # Index to original array of input points
        self.sitenum = sitenum

    def __eq__(self, other):
        return self.y == other.y and self.x == other.x

    def __lt__(self, other):
        if self.y == other.y:
            return self.x < other.x
        else:
            return self.y < other.y

    def distance(self, other):
        """"""
        return math.hypot(self.x - other.x, self.y - other.y)


class _SiteList(list):
    """A sorted list of sites with min/max point values.
    Sites will be ordered by (Y, X) but the site number will
    correspond to the initial order."""
    def __init__(self, input_points):
        """Points should be 2-tuples with x and y value."""
        super(_SiteList, self).__init__()
        self.xmin, self.ymin = input_points[0]
        self.xmax, self.ymax = input_points[0]
        for i, p in enumerate(input_points):
            site = _Site(p[0], p[1], i)
            self.append(site)
            self.xmin = min(site.x, self.xmin)
            self.ymin = min(site.y, self.ymin)
            self.xmax = max(site.x, self.xmax)
            self.ymax = max(site.y, self.ymax)
        self.sort(key=lambda site: (site.y, site.x))


class _Edge(object):
    """A Voronoi diagram edge.
    This contains the line equation and endpoints of the Voronoi segment
    as well as the endpoints of the Delaunay segment this line is bisecting.
    """
    LEFT = 0
    RIGHT = 1
    DELETED = {}   # marker value that flags an _Edge as deleted

    def __init__(self, site1, site2):
        """Create a new Voronoi edge bisecting the two sites."""
        dx = site2.x - site1.x
        dy = site2.y - site1.y
        # get the slope of the line
        slope = (site1.x * dx) + (site1.y * dy) + ((dx * dx + dy * dy) / 2)
        if abs(dx) > abs(dy):
            # set formula of line, with x fixed to 1
            self.a = 1.0
            self.b = dy / dx
            self.c = slope / dx
        else:
            # set formula of line, with y fixed to 1
            self.b = 1.0
            self.a = dx / dy
            self.c = slope / dy
        # Left and right end points of Voronoi segment.
        # By default there are no endpoints - they go to infinity.
        self.endpoints = [None, None]
        # The Delaunay segment this line is bisecting
        self.dsegment = (site1, site2)
        # Index of line and delaunay segment
        # See VoronoiDiagram._set_bisector()
        self.edgenum = -1

    def set_endpoint(self, index, site):
        """Set the value of one of the end points.
        Returns True if the other endpoint is not None."""
        self.endpoints[index] = site
        return self.endpoints[1 - index] is not None


class _HalfEdge(object):
    """"""
    def __init__(self, edge=None, orientation=_Edge.LEFT):
        # left HalfEdge in the edge list
        self.left = None
        # right HalfEdge in the edge list
        self.right = None
        # priority queue linked list pointer
        self.qnext = None
        # edge list Edge
        self.edge = edge
        #: Half edge orientation (?)
        self.orientation = orientation
        self.vertex = None
        self.ystar = sys.float_info.max

    def __cmp__(self, other):
        if self.ystar > other.ystar:
            return 1
        elif self.ystar < other.ystar:
            return -1
        elif self.vertex.x > other.vertex.x:
            return 1
        elif self.vertex.x < other.vertex.x:
            return -1
        else:
            return 0

    def left_site(self, default_site):
        """Site to the left of this half edge."""
        if not self.edge:
            return default_site
        elif self.orientation == _Edge.LEFT:
            return self.edge.dsegment[_Edge.LEFT]
        else:
            return self.edge.dsegment[_Edge.RIGHT]

    def right_site(self, default_site):
        """Site to the right of this half edge."""
        if not self.edge:
            return default_site
        elif self.orientation == _Edge.LEFT:
            return self.edge.dsegment[_Edge.RIGHT]
        else:
            return self.edge.dsegment[_Edge.LEFT]

    def is_left_of_site(self, site):
        """Returns True if site is to right of this half edge"""
        edge = self.edge
        topsite = edge.dsegment[1]
        right_of_site = site.x > topsite.x

        if right_of_site and self.orientation == _Edge.LEFT:
            return True

        if not right_of_site and self.orientation == _Edge.RIGHT:
            return False

        if _float_eq(edge.a, 1.0):
            dyp = site.y - topsite.y
            dxp = site.x - topsite.x
            fast = False
            if ((not right_of_site and edge.b < 0.0)
                    or (right_of_site and edge.b >= 0.0)):
                above = dyp >= edge.b * dxp
                fast = above
            else:
                above = site.x + site.y * edge.b > edge.c
                if edge.b < 0.0:
                    above = not above
                if not above:
                    fast = True
            if not fast:
                dxs = topsite.x - (edge.dsegment[0]).x
                above = (edge.b * (dxp*dxp - dyp*dyp) <
                         dxs * dyp * (1.0 + 2.0 * dxp / dxs + edge.b * edge.b))
                if edge.b < 0.0:
                    above = not above
        else:  # edge.b == 1.0
            y_int = edge.c - edge.a * site.x
            t1 = site.y - y_int
            t2 = site.x - topsite.x
            t3 = y_int - topsite.y
            above = (t1 * t1) > (t2 * t2 + t3 * t3)

        if self.orientation == _Edge.LEFT:
            return above
        else:
            return not above

    def intersect(self, other):
        """create a new site where the HalfEdges el1 and el2 intersect"""
        edge1 = self.edge
        edge2 = other.edge
        if edge1 is None or edge2 is None:
            return None

        # if the two edges bisect the same parent return None
        if edge1.dsegment[1] is edge2.dsegment[1]:
            return None

        dst = edge1.a * edge2.b - edge1.b * edge2.a
        if _float_eq(dst, 0.0):
            return None

        xint = (edge1.c*edge2.b - edge2.c*edge1.b) / dst
        yint = (edge2.c*edge1.a - edge1.c*edge2.a) / dst
        if edge1.dsegment[1] < edge2.dsegment[1]:
            half_edge = self
            edge = edge1
        else:
            half_edge = other
            edge = edge2

        right_of_site = xint >= edge.dsegment[1].x
        if ((right_of_site and half_edge.orientation == _Edge.LEFT)
                or (not right_of_site and
                    half_edge.orientation == _Edge.RIGHT)):
            return None

        # create a new site at the point of intersection - this is a new
        # vector event waiting to happen
        return _Site(xint, yint)


class _EdgeList(object):
    """"""
    def __init__(self, xmin, xmax, nsites):
        self.hashsize = int(2 * math.sqrt(nsites + 4))
        self.xmin = xmin
        self.hashscale = (xmax - xmin) * self.hashsize
        self.hash = [None] * self.hashsize
        self.leftend = _HalfEdge()
        self.rightend = _HalfEdge()
        self.leftend.right = self.rightend
        self.rightend.left = self.leftend
        self.hash[0] = self.leftend
        self.hash[-1] = self.rightend

    def insert(self, left, half_edge):
        """"""
        half_edge.left = left
        half_edge.right = left.right
        left.right.left = half_edge
        left.right = half_edge

    def delete(self, half_edge):
        """"""
        half_edge.left.right = half_edge.right
        half_edge.right.left = half_edge.left
        half_edge.edge = _Edge.DELETED

    def pop_leftbnd(self, site):
        """"""
        # Use hash table to get close to desired halfedge
        bucket = int((site.x - self.xmin) / self.hashscale)
        if bucket < 0:
            bucket = 0
        elif bucket >= self.hashsize:
            bucket = self.hashsize - 1

        half_edge = self._get_bucket_entry(bucket)
        if half_edge is None:
            i = 1
            while half_edge is None:
                half_edge = self._get_bucket_entry(bucket - i)
                if half_edge is None:
                    half_edge = self._get_bucket_entry(bucket + i)
                i += 1
                if (bucket - i) < 0 or (bucket + i) >= self.hashsize:
                    break

        # Now search linear list of halfedges for the correct one
        if (half_edge is self.leftend
                or (half_edge is not self.rightend
                    and half_edge.is_left_of_site(site))):
            half_edge = half_edge.right
            while (half_edge is not self.rightend
                   and half_edge.is_left_of_site(site)):
                half_edge = half_edge.right
            half_edge = half_edge.left
        else:
            half_edge = half_edge.left
            while (half_edge is not self.leftend
                   and not half_edge.is_left_of_site(site)):
                half_edge = half_edge.left

        if 0 < bucket < self.hashsize-1:
            self.hash[bucket] = half_edge

        return half_edge

    # Get the bucket entry from hash table, pruning any deleted nodes
    def _get_bucket_entry(self, b):
        half_edge = self.hash[b]
        if half_edge is not None and half_edge.edge is _Edge.DELETED:
            self.hash[b] = None
            half_edge = None
        return half_edge


class _PriorityQueue(object):
    """"""
    def __init__(self, ymin, ymax, nsites):
        self.ymin = ymin
        self.deltay = ymax - ymin
        self.hashsize = int(4 * math.sqrt(nsites))
        self.count = 0
        self.minidx = 0
#         self.hash = []
#         for dummy in range(self.hashsize):
#             self.hash.append(_HalfEdge())
        self.hash = [_HalfEdge() for dummy in range(self.hashsize)]

    def __len__(self):
        return self.count

    def is_empty(self):
        """"""
        return self.count == 0

    def insert(self, half_edge, site, offset):
        """"""
        half_edge.vertex = site
        half_edge.ystar = site.y + offset
        last = self.hash[self._get_bucket(half_edge)]
        qnext = last.qnext
        while (qnext is not None) and half_edge > qnext:
            last = qnext
            qnext = last.qnext
        half_edge.qnext = last.qnext
        last.qnext = half_edge
        self.count += 1

    def delete(self, half_edge):
        """"""
        if half_edge.vertex is not None:
            last = self.hash[self._get_bucket(half_edge)]
            while last.qnext is not half_edge:
                last = last.qnext
            last.qnext = half_edge.qnext
            half_edge.vertex = None
            self.count -= 1

    def get_min_point(self):
        """"""
        while self.hash[self.minidx].qnext is None:
            self.minidx += 1
        halfedge = self.hash[self.minidx].qnext
        return _Site(halfedge.vertex.x, halfedge.ystar)

    def pop_min_halfedge(self):
        """"""
        curr = self.hash[self.minidx].qnext
        self.hash[self.minidx].qnext = curr.qnext
        self.count -= 1
        return curr

    def _get_bucket(self, halfedge):
        """"""
        hashval = ((halfedge.ystar - self.ymin) / self.deltay)
        bucket = int(hashval * self.hashsize)
        if bucket < 0:
            bucket = 0
        if bucket >= self.hashsize:
            bucket = self.hashsize-1
        if bucket < self.minidx:
            self.minidx = bucket
        return bucket


def _float_eq(a, b):
    """Compare two floats for relative equality.

    See: http://randomascii.wordpress.com/2012/02/25/comparing-floating-point-numbers-2012-edition/
        for a discussion of floating point comparisons.
    """
    norm = max(abs(a), abs(b))
    return (norm < EPSILON) or (abs(a - b) < (EPSILON * norm))
#     return abs(a - b) < EPSILON


def jiggle(point):
    """Move a point in a random direction by a small random distance.

    Useful for when input is degenerate (i.e. when points are collinear.)

    Args:
        point: The point as a 2-tuple of the form (x, y)

    Returns:
        A new jiggled point as a 2-tuple
    """
    x, y = point
    norm_x = EPSILON * abs(x)
    norm_y = EPSILON * abs(y)
    sign = random.choice((-1, 1))
    x = x + random.uniform(norm_x * 10, norm_x * 100) * sign
    y = y + random.uniform(norm_y * 10, norm_y * 100) * sign
    return (x, y)


