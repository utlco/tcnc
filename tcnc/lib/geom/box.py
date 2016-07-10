#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
Basic 2D bounding box geometry.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import sys
import math

from . import const
from .point import P

# Full module path to resolve circular import
import lib.geom.line

# print('importing box')
# def dummy():
#     print('dummy')


class Box(tuple):
    """Two dimensional immutable rectangle defined by two points,
    the lower left corner and the upper right corner respectively.

    The sides are always assumed to be aligned with the X and Y axes.

    Useful as clipping rectangle or bounding box.
    """
    def __new__(cls, p1, p2):
        # Canonicalize the point order so that p1 is
        # always lower left.
        x1 = min(p1[0], p2[0])
        y1 = min(p1[1], p2[1])
        x2 = max(p1[0], p2[0])
        y2 = max(p1[1], p2[1])
        return tuple.__new__(Box, (P(x1, y1), P(x2, y2)))

    @staticmethod
    def from_points(points):
        """Create a Box from the bounding box of the given points."""
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
        return Box(P(xmin, ymin), P(xmax, ymax))

    @property
    def p1(self):
        """The first corner of rectangle."""
        return self[0]

    @property
    def p2(self):
        """The second corner of rectangle."""
        return self[1]

    @property
    def xmin(self):
        """Minimum X value of bounding box."""
        return self[0][0]

    @property
    def xmax(self):
        """Maximum X value of bounding box."""
        return self[1][0]

    @property
    def ymin(self):
        """Minimum Y value of bounding box."""
        return self[0][1]

    @property
    def ymax(self):
        """Maximum X value of bounding box."""
        return self[1][1]

    @property
    def center(self):
        """Return the center point of this rectangle."""
        return self.p1 + ((self.p2 - self.p1) / 2)

    def height(self):
        """Height of rectangle. (along Y axis)"""
        return self[1][1] - self[0][1]

    def width(self):
        """Width of rectangle. (along X axis)"""
        return self[1][0] - self[0][0]

    def point_inside(self, p):
        """Return True if the point is inside this rectangle."""
        return p[0] > self[0][0] and p[0] < self[1][0] \
                and p[1] > self[0][1] and p[1] < self[1][1]

    def line_inside(self, line):
        """Return True if the line segment is inside this rectangle."""
        return self.point_inside(line.p1) and self.point_inside(line.p2)

    def all_points_inside(self, points):
        """Return True if the given set of points lie inside this rectangle."""
        for p in points:
            if not self.point_inside(p):
                return False
        return True

    def buffered(self, distance):
        """Return a copy of this box with it's boundaries expanded or shrunk
        by the specified distance. Also known as buffering.

        Args:
            distance: The distance to offset.
                The box will shrink if the distance is negative.
        """
        return Box(self.p1 - distance, self.p2 + distance)

    def transform(self, matrix):
        """Return a copy of this box with the transform matrix applied to it.

        Note: rotations just scale since a Box is always aligned to
            the X and Y axes.
        """
        return Box(self[0].transform(matrix), self[1].transform(matrix))

    def clip_line(self, line):
        """If the given line segment is clipped by this rectangle then
        return a new line segment with clipped end-points.

        If the line segment is entirely within the rectangle this
        returns the same (unclipped) line segment.

        If the line segment is entirely outside the rectangle this
        returns None.

        Uses the Liang-Barsky line clipping algorithm and translates C++ code
        from: http://hinjang.com/articles/04.html

        Args:
            line: The line segment to clip.

        Returns:
            A new clipped line segment or None if the segment does
            not intersect.
        """
        if self.line_inside(line):
            return line
        x1 = line.p1.x
        y1 = line.p1.y
        x2 = line.p2.x
        y2 = line.p2.y
        dx = x2 - x1
        dy = y2 - y1
        u_minmax = [0.0, 1.0]
        if (self._clipT(self.xmin - x1, dx, u_minmax)
                and self._clipT(x1 - self.xmax, -dx, u_minmax)
                and self._clipT(self.ymin - y1, dy, u_minmax)
                and self._clipT(y1 - self.ymax, -dy, u_minmax)):
            if u_minmax[1] < 1.0:
                x2 = x1 + u_minmax[1] * dx
                y2 = y1 + u_minmax[1] * dy
            if u_minmax[0] > 0.0:
                x1 += u_minmax[0] * dx
                y1 += u_minmax[0] * dy
            return lib.geom.line.Line(P(x1, y1), P(x2, y2))
        return None

    def _clipT(self, nQ, nP, u_minmax):
        """Lian-Barsky helper"""
        if const.is_zero(nP):
            # line is parallel to box edge - is it outside the box?
            return nQ <= 0.0
        u = nQ / nP
        if nP > 0.0:
            # line goes from inside box to outside
            if u > u_minmax[1]:
                return False
            elif u > u_minmax[0]:
                u_minmax[0] = u
        else:
            # line goes from outside to inside
            if u < u_minmax[0]:
                return False
            elif u < u_minmax[1]:
                u_minmax[1] = u
        return True

    def start_tangent_angle(self):
        """Return the angle in radians of a line tangent to this shape
        beginning at the first point.

        The corner point order for rectangles is clockwise from lower left.
        """
        return math.pi / 2

    def bounding_box(self):
        """Bounding box - self."""
        return self

    def intersection(self, other):
        """Return a Box that is the intersection of this rectangle and another.

        Returns None if the rectangles do not intersect.
        """
        other = other.bounding_box()
        xmin = max(self.xmin, other.xmin)
        xmax = min(self.xmax, other.xmax)
        ymin = max(self.ymin, other.ymin)
        ymax = min(self.ymax, other.ymax)
        if xmin > xmax or ymin > ymax:
            return None
        else:
            return Box((xmin, ymin), (xmax, ymax))

    def union(self, other):
        """Return a Box that is the union of this rectangle and another.
        """
        other = other.bounding_box()
        xmin = min(self.xmin, other.xmin)
        xmax = max(self.xmax, other.xmax)
        ymin = min(self.ymin, other.ymin)
        ymax = max(self.ymax, other.ymax)
        return Box((xmin, ymin), (xmax, ymax))

#     def rectangle(self):
#         """Return an equivalent shape as a rectangular polygon."""
#         return parallelogram.Parallelogram(P(self.xmin, self.ymin), P(self.xmin, self.ymax),
#                          P(self.xmax, self.ymax), P(self.xmax, self.ymin))

Box.__and__ = Box.intersection
"""Alias of :method:`Box.intersection()`"""
Box.__or__ = Box.union
"""Alias of :method:`Box.union()`"""
