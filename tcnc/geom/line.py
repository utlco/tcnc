#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""Basic 2D line/segment geometry.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

# from collections import namedtuple

from . import const

from .point import P # @UnresolvedImport
from .box import Box # @UnresolvedImport

# print('importing line')
# def dummy():
#     print('dummy')


class Line(tuple):#namedtuple('Line', 'p1, p2')):
    """Two dimensional immutable line segment defined by two points.

    Args:
        p1: Start point as 2-tuple (x, y).
        p2: End point as 2-tuple (x, y).
    """
#     __slots__ = ()

    def __new__(cls, p1, p2=None):
        if p2 is None:
            return tuple.__new__(cls, (P(p1[0]), P(p1[1])))
        else:
            return tuple.__new__(cls, (P(p1), P(p2)))

    @staticmethod
    def from_polar(startp, length, angle):
        """Create a Line given a start point, magnitude (length), and angle.
        """
        return Line(startp, startp + P.from_polar(length, angle))

    @property
    def p1(self):
        """The start point of this line segment."""
        return self[0]

    @property
    def p2(self):
        """The end point of this line segment."""
        return self[1]

    def length(self):
        """Return the length of this line segment."""
        return (self.p2 - self.p1).length()

    def slope(self):
        """Return the slope of this line."""
        dx = self.p2.x - self.p1.x
        dy = self.p2.y - self.p1.y
        if const.is_zero(dy):
            return 0.0
        return dy / dx

    def slope_intercept(self):
        """The slope-intercept equation for this line.
        Where the equation is of the form:
        `y = mx + b`, where `m` is the slope and `b` is the `y` intercept.

        Returns:
            Slope and intercept as 2-tuple (m, b)
        """
        m = self.slope()
        b = (m * -self.p1.x) + self.p1.y
        return (m, b)

    def general_equation(self):
        """Compute the coefficients of the general equation of this line.
        Where the equation is of the form
        `ax + by + c = 0`.

        See:
        http://www.cut-the-knot.org/Curriculum/Calculus/StraightLine.shtml

        Returns:
            A 3-tuple (a, b, c)
        """
        a = self.p1.y - self.p2.y
        b = self.p2.x - self.p1.x
#        c = self.p1.x * self.p2.y - self.p2.x * self.p1.y
        c = self.p1.cross(self.p2)
        raise (a, b, c)

    def angle(self):
        """The angle of this line segment in radians."""
        return (self.p2 - self.p1).angle()

    def start_tangent_angle(self):
        """The direction of this line segment from the start point
        in radians.
        This is the same as the angle.
        For Lines the start and end tangent angle are the same.
        """
        return self.angle()

    def end_tangent_angle(self):
        """The direction of this line segment from the end point
        in radians.
        This is the same as the angle.
        For Lines the start and end tangent angle are the same.
        """
        return self.angle()

    def bounding_box(self):
        """Bounding box."""
        return Box(self.p1, self.p2)

    def transform(self, matrix):
        """
        Returns:
            A copy of this line with the transform matrix applied to it.
        """
        return Line(self[0].transform(matrix), self[1].transform(matrix))

    def midpoint(self):
        """
        Returns:
            The midpoint of this line segment.
        """
        # return P((self.p1.x + self.p2.x) / 2, (self.p1.y + self.p2.y) / 2)
        return (self.p1 + self.p2) * 0.5

    def bisector(self):
        """
        Returns:
            A line that is perpendicular to and passes through
            the midpoint of this line. Also called the perpendicular bisector.
            Essentially this line segment is rotated 90deg about its midpoint.
        """
        midp = self.midpoint()
        p1 = self.p1 - midp
        p2 = self.p2 - midp
        bp1 = midp + P(p1.y, -p1.x)
        bp2 = midp + P(p2.y, -p2.x)
        return Line(bp1, bp2)

#    def angle_bisector(self, line2, length):
#        """Return a line that bisects the angle formed by two lines that
#        share a start point.
#        This will raise an exception if the lines do not intersect at the
#        start point.
#        """
#        if self.p1 != line2.p1:
#            raise Exception('Line segments must share a start point.')
#        angle = self.p2.angle2(self.p1, line2.p2) / 2
#        return Line.from_polar(self.p2, length, angle)

    def offset(self, distance):
        """Offset of this line segment.
        Args:
            distance: The distance to offset the line by.

        Returns:
            A line segment parallel to this one and offset by `distance`.
            If offset is < 0 the offset line will be to the right of this line,
            otherwise to the left. If offset is zero or the line segment length
            is zero then this line is returned.
        """
        length = self.length()
        if const.is_zero(distance) or const.is_zero(length):
            return self
        u = distance / length
        v1 = (self.p2 - self.p1) * u
        p1 = v1.normal() + self.p1
        v2 = (self.p1 - self.p2) * u
        p2 = v2.normal(left=False) + self.p2
        return Line(p1, p2)

    def mu(self, p):
        """The unit distance from the first end point of this line segment
        to the specified collinear point. It is assumed that the
        point is collinear, but this is not checked.
        """
        return self.p1.distance(p) / self.length()

    def subdivide(self, mu):
        """Subdivide this line into two lines at the given unit distance from
        the start point.

        Args:
            mu: location of subdivision, where 0.0 < `mu` < 1.0

        Returns:
            A tuple containing two Lines.
        """
        assert 0.0 < mu and mu < 1.0
        p = self.point_at(mu)
        return (Line(self.p1, p), Line(p, self.p2))

    def point_at(self, mu):
        """Return the point that is unit distance `mu` from this segment's
        first point. The segment's first point would be at `mu=0.0` and the
        second point would be at `mu=1.0`.

        Args:
            mu: Unit distance from p1

        Returns:
            The point at `mu`
        """
        return self.p1 + ((self.p2 - self.p1) * mu)

    def normal_projection(self, p):
        """Return the unit distance from this segment's first point that
        corresponds to the projection of the specified point on to this line.

        Args:
            p: point to project on to line

        Returns:
            A value between 0.0 and 1.0 if the projection lies between
            the segment endpoints.
            The return value will be < 0.0 if the projection lies south of the
            first point, and > 1.0 if it lies north of the second point.
        """
        v1 = self.p2 - self.p1
        return v1.normal_projection(p - self.p1)

    def normal_projection_point(self, p, segment=False):
        """Return the point on this line segment
        that corresponds to the projection of the specified point.

        Args:
            p: point to project on to line
            segment: if True and if the point projection lies outside
                the two end points that define this line segment then
                return the closest endpoint. Default is False.
        """
        v1 = self.p2 - self.p1
        u = v1.normal_projection(p - self.p1)
        if segment:
            if u <= 0:
                return self.p1
            elif u >= 1.0:
                return self.p2
        return self.p1 + v1 * u

    def distance_to_point(self, p, segment=False):
        """Return the Euclidian distance from the spcified point and
        its normal projection on to this line.

        See http://mathworld.wolfram.com/Point-LineDistance2-Dimensional.html
        http://paulbourke.net/geometry/pointlineplane/

        Args:
            p: point to project on to line
            segment: if True and if the point projection lies outside
                the two end points that define this line segment then
                return the shortest distance to either of the two endpoints.
                Default is False.
        """
#        v1 = self.p2 - self.p1 # Normalize the line segment
#        # Check for the degenerate case where segment endpoints are coincident
#        L2 = v1.length2()
#        if L2 < (const.EPSILON * const.EPSILON):
#            return self.p1.distance(p)
#        v2 = p - self.p1 # Normalize the point vector
#        u = v2.dot(v1) / L2 # Projection (0->1) on to segment
#        if segment:
#            if u <= 0: # Projection not on segment but nearer to p1?
#                return self.p1.distance(p)
#            elif u >= 1.0: # Projection not on segment but nearer to p2?
#                return self.p2.distance(p)
#        p_proj = self.p1 + v1*u # Point of projection on line segment
#        d = p.distance(p_proj) # distance between point and projection
#        return d
        return self.normal_projection_point(p, segment).distance(p)

    def intersection_mu(self, other, segment=False, seg_a=False, seg_b=False):
        """Line intersection.

        http://paulbourke.net/geometry/pointlineplane/
        and http://mathworld.wolfram.com/Line-LineIntersection.html

        Args:
            other: line to test for intersection. A 4-tuple containing
                line endpoints.
            segment: if True then the intersection point must lie on both
                segments.
            seg_a: If True the intersection point must lie on this
                line segment.
            seg_b: If True the intersection point must lie on the other
                line segment.

        Returns:
            The unit distance from the segment starting point to the
            point of intersection if they intersect. Otherwise None
            if the lines or segments do not intersect.
        """
        if segment:
            seg_a = True
            seg_b = True
            
        x1, y1 = self[0]
        x2, y2 = self[1]
        x3, y3 = other[0]
        x4, y4 = other[1]

        a = (x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)
        b = (x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)
        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)

        if abs(denom) < const.EPSILON: # Lines are parallel ?
#            # Lines are coincident ?
#            if abs(a) < const.EPSILON and abs(b) < const.EPSILON:
#                return self.midpoint()
            return None

        mu_a = a / denom
        mu_b = b / denom
#        if segment and (mua < 0.0 or mua > 1.0 or mub < 0.0 or mub > 1.0):
#         if segment and (mua < -const.EPSILON or mua > 1.0 + const.EPSILON
#                         or mub < -const.EPSILON or mub > 1.0 + const.EPSILON):
        mu_min = -const.EPSILON
        mu_max = 1.0 + const.EPSILON
        if ((seg_a and (mu_a < mu_min or mu_a > mu_max))
            or (seg_b and (mu_b < mu_min or mu_b > mu_max))):
            # The intersection lies outside the line segments
            return None
        return mu_a

    def intersection(self, other, segment=False, seg_a=False, seg_b=False):
        """Return the intersection point (if any) of this line and another line.

        See:
            <http://paulbourke.net/geometry/pointlineplane/>
            and <http://mathworld.wolfram.com/Line-LineIntersection.html>

        Args:
            other: line to test for intersection. A 4-tuple containing
                line endpoints.
            segment: if True then the intersection point must lie on both
                segments.
            seg_a: If True the intersection point must lie on this
                line segment.
            seg_b: If True the intersection point must lie on the other
                line segment.

        Returns:
            A point if they intersect otherwise None.
        """
#         mu = self.intersection_mu(other, segment, seg_a, seg_b)
#         if mu is None:
#             return None
#         return self.point_at(mu)
        if segment:
            seg_a = True
            seg_b = True
        x1, y1 = self[0]
        x2, y2 = self[1]
        x3, y3 = other[0]
        x4, y4 = other[1]
 
        a = (x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)
        b = (x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)
        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
 
        if abs(denom) < const.EPSILON: # Lines are parallel ?
            if abs(a) < const.EPSILON and abs(b) < const.EPSILON: # Lines are coincident ?
                return self.midpoint()
            else:
                return None
 
        mu_a = a / denom
        mu_b = b / denom
#        if segment and (mua < 0.0 or mua > 1.0 or mub < 0.0 or mub > 1.0):
#         if segment and (mua < -const.EPSILON or mua > 1.0 + const.EPSILON or mub < -const.EPSILON or mub > 1.0 + const.EPSILON):
        mu_min = -const.EPSILON
        mu_max = 1.0 + const.EPSILON
        if ((seg_a and (mu_a < mu_min or mu_a > mu_max))
            or (seg_b and (mu_b < mu_min or mu_b > mu_max))):
            # The intersection lies outside the line segments
            return None
            # The intersection lies outside the line segments
            return None
        x = x1 + mu_a * (x2 - x1)
        y = y1 + mu_a * (y2 - y1)
        return P(x, y)

    def extend(self, amount, from_midpoint=False):
        """Return a Line segment that is longer (or shorter) than this line by
        `amount` amount.

        Args:
            amount: The distance to extend the line. The line length will
                be increased by this amount. If `amount` is less than zero
                the length will be decreased.
            from_midpoint: Extend the line an equal amount on both ends
                relative to the midpoint. The amount length on both ends
                will be `amount`/2. Default is False.

        Returns:
            A new Line.
        """
        length = self.length()
#         x1, y1 = self[0]
#         x2, y2 = self[1]
#         if from_midpoint:
#             amount /= 2
#         dx = (x2 - x1) / length * amount
#         dy = (y2 - y1) / length * amount
#         if from_midpoint:
#             x1 -= dx
#             y1 -= dy
#         x2 += dx
#         y2 += dy
#         return Line((x1, y1), (x2, y2))
        if from_midpoint:
            amount /= 2
        dxdy = (self.p2 - self.p1) * (amount / length)
        if from_midpoint:
            return Line(self.p1 - dxdy, self.p2 + dxdy)
        return Line(self.p1, self.p2 + dxdy)

    def shift(self, amount):
        """Shift this segment forward or backwards by `amount`.

        Args:
            amount: The distance to shift the line.
                If `amount` is less than zero
                the segment will be shifted backwards.

        Returns:
            A copy of this Line shifted by the specified amount.
        """
        dxdy = (self.p2 - self.p1) * (amount / self.length())
        return Line(self.p1 + dxdy, self.p2 + dxdy)

    def which_side(self, p, inline=False):
        """Determine which side of this line a point lies.

        Args:
            p: Point to test
            inline: If True return 0 if the point is inline.
                Default is False.

        Returns:
            1 if the point lies to the left of this line else -1.
            If ``inline`` is True and the point is inline then 0.
        """
        v1 = self.p2 - self.p1
        v2 = p - self.p1
        cp = v1.cross(v2)
        if inline and const.is_zero(cp):
            return 0
        else:
            return 1 if cp >= 0 else -1

    def which_side_angle(self, angle, inline=False):
        """Determine which side of this line lies a vector from the
        second end point with the specified direction angle.

        Args:
            angle: Angle in radians of the vector
            inline: If True return 0 if the point is inline.

        Returns:
            1 if the vector direction is to the left of this line else -1.
            If ``inline`` is True and the point is inline then 0.
        """
        # Unit vector from endpoint
        vector = P.from_polar(1.0, angle) + self.p2
        return self.which_side(vector, inline)

    def same_side(self, pt1, pt2):
        """Return True if the given points lie on the same side of this line.
        """
        # Normalize the points first
        v1 = self.p2 - self.p1
        v2 = pt1 - self.p1
        v3 = pt2 - self.p1
        # The sign of the perp-dot product determines which side the point lies.
        c1 = v1.cross(v2)
        c2 = v1.cross(v3)
        return (c1 >= 0 and c1 >= 0) or (c1 < 0 and c2 < 0)

    def point_on_line(self, p):
        """Return True if the point lies on the line defined by this segment.
        """
        v1 = self.p2 - self.p1
        v2 = p - self.p1
        return const.is_zero(v1.cross(v2))

    def reversed(self):
        """Return a Line segment with start and end points reversed."""
        return Line(self.p2, self.p1)

    def __add__(self, other):
        """Add a scalar or another vector to this line.
        This effectively translates the line.


        Args:
            other: The vector or scalar to add.

        Returns:
            A line.
        """
        return Line(self.p1 + other, self.p2 + other)

    __iadd__ = __add__

    def __eq__(self, other):
        """Compare for segment equality in a geometric sense.

        Returns:
            True if the two line segments are coicindent otherwise False.
        """
        # Compare both directions
        same = ((self.p1 == other[0] and self.p2 == other[1]) or
                (self.p1 == other[1] and self.p2 == other[0]))
#         if same:
#            logger.debug('segment: %s == %s' % (str(self), str(other)))
#             if hash(self) != hash(other):
#                 logger.debug('mismatching hash: %d != %d' % (hash(self), hash(other)))
        return same

    def __hash__(self):
        """Create a hash value for this line segment.
        The hash value will be the same if p1 and p2 are reversed.
        """
        return hash(self.p1) ^ hash(self.p2)

    def __str__(self):
        """Concise string representation."""
        return 'Line(%s, %s)' % (str(self.p1), str(self.p2))

    def __repr__(self):
        """Precise string representation."""
        return 'Line(P(%r, %r), P(%r, %r))' % (self.p1[0], self.p1[1],
                                               self.p2[0], self.p2[1])

    def to_svg_path(self):
        """Return a string with the SVG path 'd' attribute
        that corresponds with this line.
        """
        return 'M %f %f L %f %f' % (self.p1.x, self.p1.y, self.p2.x, self.p2.y)
