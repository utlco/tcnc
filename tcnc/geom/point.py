#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
Basic 2D point/vector.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import sys
import math
# from collections import namedtuple

from . import transform2d
from . import const
from . import util


# pylint: disable=too-many-public-methods
class P(tuple):#namedtuple('P', 'x, y')):
    """Two dimensional immutable point (vector).

    Represented as a simple tuple (x, y) so that it is compatible with many
    other libraries.

    If ``y`` is None ``x`` is assumed to be a tuple or list containing
    both x and y.

    Args:
        x: X coordinate. Type float.
        y: Y coordinate. Type float.
    """
    __slots__ = ()

    def __new__(cls, x, y=None):
        """"""
        if y is None:
            return tuple.__new__(cls, ((float(x[0]), float(x[1]))))
        else:
            return tuple.__new__(cls, ((float(x), float(y))))

    @property
    def x(self):
        """The X (horizontal) coordinate."""
        return self[0]

    @property
    def y(self):
        """The Y (vertical) coordinate."""
        return self[1]

    @staticmethod
    def max_point():
        """Create a point with max X and Y values."""
        return P(sys.float_info.max, sys.float_info.max)

    @staticmethod
    def min_point():
        """Create a point with min X and Y values."""
        return P(sys.float_info.min, sys.float_info.min)

    @staticmethod
    def from_polar(r, angle):
        """Create a Cartesian point from polar coordinates.

        See http://en.wikipedia.org/wiki/Polar_coordinate_system

        Args:
            r: Magnitude (radius)
            angle: Angle in radians

        Returns:
            A point.
        """
        x = r * math.cos(angle)
        y = r * math.sin(angle)
        return P(x, y)

    def to_polar(self):
        """Return the polar coordinates of this vector as a tuple
        containing the magnitude (radius) and angle respectively (r, a).
        """
        return (self.length(), self.angle())

    def is_zero(self):
        """Return True if X and Y are both within EPSILON distance to zero."""
        return self.length2() < (const.EPSILON * const.EPSILON)

    def almost_equal(self, other, tolerance=None):
        """Compare points for geometric equality.

        Args:
            other: Vector (point) being compared. A 2-tuple (x, y).
            tolerance: Max distance between the two points.
                Default is ``EPSILON``.

        Returns:
            True if distance between the points < `tolerance`.
        """
        if tolerance is None:
            tolerance = const.EPSILON
        dx = self[0] - other[0]
        dy = self[1] - other[1]
        return (dx * dx + dy * dy) < (tolerance * tolerance)

    def length(self):
        """The length or scalar magnitude of the vector.

        Returns:
            Distance from (0, 0).
        """
        return math.hypot(self[0], self[1])

    def length2(self):
        """The square of the length of the vector."""
        x, y = self
        return x * x + y * y

    def unit(self):
        """The vector scaled to unit length. If the vector
        length is zero, a null (0, 0) vector is returned.

        Returns:
            A copy of this vector scaled to unit length.
        :return type: P
        """
        L2 = self.length2()
        if L2 > (const.EPSILON * const.EPSILON):
            L = math.sqrt(L2)
            return P(self[0] / L, self[1] / L)
        else:
            return P(0.0, 0.0)

    def normal(self, left=True):
        """Return a vector perpendicular to this one.

        Args:
            left: left of vector if True, otherwise right. Default is True.
        """
        if left:
            return P(-self[1], self[0])
        else:
            return P(self[1], -self[0])

    def dot(self, other):
        """Compute the dot product with another vector.

        Equivalent to \|p1\|\*\|p2\|\*cos(theta) where theta is the
        angle between the two vectors.

        See:
            http://en.wikipedia.org/wiki/Dot_product

        Args:
            other: The vector with which to compute the dot product.
                A 2-tuple (x, y).

        Returns:
            A scalar dot product.
        """
        x2, y2 = other
        return self[0] * x2 + self[1] * y2

    def cross(self, other):
        """Compute the cross product with another vector.
        Also called the perp-dot product for 2D vectors.
        Also called determinant for 2D matrix.

        See:
            http://mathworld.wolfram.com/PerpDotProduct.html
            http://www.gamedev.net/topic/441590-2d-cross-product/

        From Woodward:
        The cross product generates a new vector perpendicular to the two
        that are being multiplied, with a length equal to the (ordinary)
        product of their lengths.

        Args:
            other: The vector with which to compute the cross product.

        Returns:
            A scalar cross product.
        """
        x2, y2 = other
        return self[0] * y2 - x2 * self[1]

    def angle(self):
        """The angle of this vector relative to the x axis in radians.

        Returns:
            A float value between -pi and pi.
        """
        return math.atan2(self[1], self[0])

    def angle2(self, p1, p2):
        """The angle formed by p1->self->p2.

        The angle is negative if p1 is to the left of p2.

        Args:
            p1: First point as 2-tuple (x, y).
            p2: Second point as 2-tuple( x, y).

        Returns:
            The angle in radians between -pi and pi.
            Returns 0 if points are coincident.
        """
        v1 = P(p1) - self
        v2 = P(p2) - self
        if v1 == v2:
            return 0.0
        # return math.acos(v1.dot(v2))
        # Apparently this is more accurate for angles near 0 or PI:
        # see http://www.mathworks.com/matlabcentral/newsreader/view_thread/151925
        return math.atan2(v1.cross(v2), v1.dot(v2))

    def ccw_angle2(self, p1, p2):
        """The counterclockwise angle formed by p1->self->p2.

        Args:
            p1: First point as 2-tuple (x, y).
            p2: Second point as 2-tuple( x, y).

        Returns:
            An angle in radians between 0 and 2*math.pi.
        """
        a = self.angle2(p1, p2)
        return util.normalize_angle(a, center=math.pi)

    def bisector(self, p1, p2):
        """The bisector between the angle formed by p1->self->p2.

        Args:
            p1: First point as 2-tuple (x, y).
            p2: Second point as 2-tuple (x, y).

        Returns:
            A unit vector with origin at `self`.
        """
        a1 = (p1 - self).angle()
        a2 = (p2 - self).angle()
        a3 = (a1 + a2) / 2
        return self + P.from_polar(1.0, a3)

    def distance(self, p):
        """Euclidean distance from this point to another point.

        Args:
            p: The other point as a 2-tuple (x, y).

        Returns:
            The Euclidean distance.
        """
        return math.hypot(self[0] - p[0], self[1] - p[1])

    def distance2(self, p):
        """Euclidean distance squared to other point.
        This can be used to compare distances without the
        expense of a sqrt."""
        a = self[0] - p[0]
        b = self[1] - p[1]
        return (a * a) + (b * b)

    def distance_to_line(self, p1, p2):
        """Euclidean distance from this point to it's normal projection
        on a line that intersects the given points.

        See:
            http://mathworld.wolfram.com/Point-LineDistance2-Dimensional.html
            http://local.wasp.uwa.edu.au/~pbourke/geometry/pointline/

        Args:
            p1: First point on line.
            p2: Second point on line.

        Returns:
            Normal distance to line.
        """
        p1 = P(p1)
        p2 = P(p2)
        v1 = p2 - p1 # Normalize the line segment
        seglen = v1.length() # Segment length
        if seglen < const.EPSILON: # Degenerate line segment...?
            return self.distance(p1) # TBD: This should probably be undefined...

        v2 = p1 - self
        return v1.cross(v2) / seglen

#     def distance_to_segment(self, p1, p2):
#         """Euclidean distance from this point to a line segment defined by
#         the given start and end points.
#
#         Args:
#             p1: Start point of line segment.
#             p2: End point of line segment.
#
#         Returns:
#             The normal distance to the line segment. If this point's
#             projection doesn't fall on the line segment then
#             return the distance from this point to the closest
#             segment endpoint.
#         """
#         seg = line.Line(p1, p2)
#         return seg.distance_to_point(self, segment=True)

    def normal_projection(self, p):
        """The unit distance from the origin that corresponds to
        the projection of the specified point on to the line described by
        this vector.

        Args:
            p: A vector (point) as 2-tuple (x, y).
        """
        # Check for the degenerate case where the vector has zero length
        L2 = self.length2()
        if L2 < (const.EPSILON * const.EPSILON):
            return 0
        return P(p).dot(self) / L2

    def inside_triangle2D(self, A, B, C):
        """Test if this point lies inside the triangle defined
        by points A, B, and C.
        Where ABC is clockwise or counter-clockwise.

        See http://www.sunshine2k.de/stuff/Java/PointInTriangle/PointInTriangle.html

        Args:
            A: First point of triangle as 2-tuple (x, y)
            B: Second point of triangle as 2-tuple (x, y)
            C: Third point of triangle as 2-tuple (x, y)

        Returns:
            True if this point lies within the triangle ABC.
        """
        # Using barycentric coordinates
        v1 = B - A
        v2 = C - A
        v3 = self -A
        det = v1.cross(v2)
        s = v1.cross(v3) / det
        t = v2.cross(v3) / det
        return s >= 0.0 and t >= 0.0 and (s + t) <= 1

    def orientation(self, p2, p3):
        """Determine the direction defined by the three points
        p1->p2->p3. `p1` being this point.

        Args:
            p2: Second point as 2-tuple (x, y).
            p3: Third point as 2-tuple (x, y).

        Returns:
            Positive if self->p2->p3 is clockwise (right),
            negative if counterclockwise (left),
            zero if points are colinear.
        """
        return (P(p2) - self).cross(P(p3) - self)

    def transform(self, matrix):
        """Return a copy of this point with the transform matrix applied to it.
        """
        return P(transform2d.matrix_apply_to_point(matrix, self))

    def rotate(self, angle, origin=(0.0, 0.0)):
        """Return a copy of this point rotated about the origin by `angle`."""
        return self.transform(transform2d.matrix_rotate(angle, origin))

    def __eq__(self, other):
        """Compare for equality.

        Uses EPSILON to compare point values so that spatial hash tables
        and other geometric comparisons work as expected.
        There may be cases where an exact compare is necessary but for
        most purposes (like collision detection) this works better.

        See:
            P.almost_equal()
        """
        return other is not None and self.almost_equal(other)

    def __ne__(self, other):
        """Compare for inequality."""
        return other is None or not self.almost_equal(other)

    def __nonzero__(self):
        """Return True if this is not a null vector.

        See:
            P.is_zero()
        """
        return not self.is_zero()

    def __neg__(self):
        """Return the unary negation of the vector (-x, -y)."""
        return P(-self[0], -self[1])

    def __add__(self, other):
        """Add the vector to a scalar or another vector.

        Args:
            other: The vector or scalar to add.

        Returns:
            A vector (point).
        """
        try:
            n = float(other)
            return P(self[0] + n, self[1] + n)
        except TypeError:
            x2, y2 = other
            return P(self[0] + x2, self[1] + y2)

    __iadd__ = __add__

    def __sub__(self, other):
        """Subtract a scalar or another vector from this vector.

        Args:
            other: The vector or scalar to substract.

        Returns:
            A vector (point).
        """
        try:
            n = float(other)
            return P(self[0] - n, self[1] - n)
        except TypeError:
            x2, y2 = other
            return P(self[0] - x2, self[1] - y2)

    __isub__ = __sub__

    def __mul__(self, other):
        """Multiply the vector by a scalar. This operation is undefined
        for any other type since it doesn't make geometric sense. Use dot()
        or cross() instead.

        Args:
            other: The scalar to multiply by.
        """
        return P(self[0] * other, self[1] * other)

    __rmul__ = __imul__ = __mul__

    def __truediv__(self, other):
        """Divide the vector by a scalar.

        Args:
            other: A scalar value to divide by.
        """
        return tuple.__new__(P, (self[0] / other, self[1] / other))

    __idiv__ = __div__ = __itruediv__ = __truediv__

    def __floordiv__(self, other):
        """Divide the vector by a scalar, rounding down.

        Args:
            other: The value to divide by.
        """
        return tuple.__new__(P, (self[0] // other, self[1] // other))

    __ifloordiv__ = __floordiv__

    def __pos__(self):
        return self

    def __abs__(self):
        """Compute the absolute magnitude of the vector."""
        return self.length()

    def __str__(self):
        """Concise string representation."""
        point_fmt = '%%.%df, %%.%df' % (const.EPSILON_PRECISION,
                                        const.EPSILON_PRECISION)
        return 'P(%s)' % (point_fmt % self)

    def __repr__(self):
        """Precise string representation."""
        return 'P(%r, %r)' % self

    def __hash__(self):
        """
        Calculate a spatial hash value for this point that can be used
        for basic collision detection. Uses the precision specified by
        EPSILON to round off coordinate values.

        See:
            http://www.beosil.com/download/CollisionDetectionHashing_VMV03.pdf
        """
        # The coordinate values are first rounded down to the current
        # level of precision (see EPSILON) so that floating point
        # artifacts and small differences in spatial distance
        # (spatial jitter) are filtered out.
        # This seems to work pretty well in practice.
        a = int(round(self[0], const.EPSILON_PRECISION)) * 73856093
        b = int(round(self[1], const.EPSILON_PRECISION)) * 83492791
        # This commented out code may be slightly faster but I suspect
        # it has less entropy in the lower bits.
#         repsilon = 10 ** const.EPSILON_PRECISION
#         a = int(round(self[0] * repsilon)) * 73856093
#         b = int(round(self[1] * repsilon)) * 83492791
        # Modulo largest 32 bit Mersenne prime. The intent is
        # to minimize collisions by creating a slightly better
        # distribution over the 32 bit integer range.
        hashval = (a ^ b) % 2147483647
        # TODO: Revisit Rob Jenkins or Thomas Wang's integer hash functions
        # See:
        #    https://web.archive.org/web/20071223173210/http://www.concentric.net/~Ttwang/tech/inthash.htm
        #    http://burtleburtle.net/bob/hash/doobs.html
        #    http://burtleburtle.net/bob/c/lookup3.c
        #    http://burtleburtle.net/bob/hash/integer.html
        return hashval


# Make some method aliases to be compatible with various Point implementations
P.mag = P.length
"""Alias of :method:`P.length()`"""
P.normalized = P.unit
"""Alias of :method:`P.unit()`"""
P.perpendicular = P.normal
"""Alias of :method:`P.normal()`"""

