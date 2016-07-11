#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
Cubic bezier curve.

Includes biarc approximation.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import math
# import logging

from . import const
from . import util
from . import transform2d

from .point import P
from .line import Line
from .arc import Arc

# logger = logging.getLogger(__name__)

class CubicBezier(tuple):
    """Two dimensional immutable cubic bezier curve.

    For information about Bezier curves see:
    https://pomax.github.io/bezierinfo

    Args:
        p1: Start point as 2-tuple (x, y).
        c1: First control point as 2-tuple (x, y).
        c2: Second control point as 2-tuple (x, y).
        p2: End point as 2-tuple (x, y).
    """
    def __new__(cls, p1, c1, c2, p2):
        return tuple.__new__(CubicBezier, (P(p1), P(c1), P(c2), P(p2)))

    @staticmethod
    def from_quadratic(qp1, qp2, qp3):
        """Create a CubicBezier from the control points of a quadratic
        Bazier curve.

        Args:
            qp1: Start point as 2-tuple (x, y).
            qp2: Control point as 2-tuple (x, y).
            qp3: End point as 2-tuple (x, y).
        """
        qp2 = P(qp2)
        p1 = P(qp1)
        p2 = P(qp3)
        c1 = p1 + (2.0 * (qp2 - p1)) / 3.0
        c2 = p2 + (2.0 * (qp2 - p2)) / 3.0
        return CubicBezier(p1, c1, c2, p2)

    @property
    def p1(self):
        """The start point of curve."""
        return self[0]

    @property
    def c1(self):
        """The first control point of curve."""
        return self[1]

    @property
    def c2(self):
        """The second control point of curve."""
        return self[2]

    @property
    def p2(self):
        """The end point of curve."""
        return self[3]

    def transform(self, matrix):
        """Return a copy of this curve with the transform matrix applied to it.
        """
        return CubicBezier(self[0].transform(matrix), self[1].transform(matrix),
                           self[2].transform(matrix), self[3].transform(matrix))

    def start_tangent_angle(self):
        """Return the tangent direction of this curve in radians
        at the start (first) point.
        This would normally be the same as the angle of the
        first control point vector, unless the control point is
        coincident with the first point.
        -PI < angle < PI."""
        return self.tangent_at(0.0).angle()

    def end_tangent_angle(self):
        """Return the tangent direction of this curve in radians
        at the end (second) point.
        This would normally be the angle of the second control point vector
        plus PI, unless the control point is
        coincident with the second point.
        -PI < angle < PI."""
        return util.normalize_angle(self.tangent_at(1.0).angle() + math.pi,
                                    center=0.0)

    def point_at(self, t):
        """A point on the curve corresponding to <t>.
        """
        if const.is_zero(t):
            return self.p1
        elif const.float_eq(t, 1.0):
            return self.p2
        return (self.p1 * (1 - t)**3 +
                self.c1 * t * 3 * (1 - t)**2 +
                self.c2 * t**2 * 3 * (1-t) +
                self.p2 * t**3)

    def midpoint(self):
        """
        Returns:
            The point at the middle of the Bezier curve.
        """
        return self.point_at(0.5)

    def tangent_at(self, t):
        """The tangent vector at the point on the curve corresponding to `t`.
        """
        if const.is_zero(t):
            if self.c1 == self.p1:
                v = self.c2 - self.p1
            else:
                v = self.c1 - self.p1
        elif const.float_eq(t, 1.0):
            if self.c2 == self.p2:
                v = self.c2 - self.p1
            else:
                v = self.c2 - self.p2
        else:
            v = ((self.c1 - self.p1) * 3 * (1 - t)**2 +
                    (self.c2 - self.c1) * 6 * t * (1 - t) +
                    (self.p2 - self.c2) * 3 * t**2)
        return v

    def is_straight_line(self, flatness=None):
        """Return True if curve is essentially a straight line.

        Args:
            flatness: The required flatness tolerance to be considered a line.
                Default is geom.const.EPSILON.
        """
        if flatness is None:
            flatness = const.EPSILON
        return ((self.p1 == self.c1 and self.p2 == self.c2) or
                self.flatness() < flatness)

    def flatness(self):
        """Return the flatness of this curve.

        The maximum distance between the control points and the line segment
        defined by the start and end points of the curve.
        This is known as convex hull flatness and is robust regarding
        degenerate curves.
        """
        chord = Line(self.p1, self.p2)
        d1 = chord.distance_to_point(self.c1, segment=True)
        d2 = chord.distance_to_point(self.c2, segment=True)
        return max(d1, d2)

    def subdivide(self, t):
        """Subdivide this curve at the point corresponding to <t>
        into two cubic bezier curves, where 0<=t<=1.
        Uses De Casteljaus's algorithm.

        Returns:
            A tuple of one or two CubicBezier objects.
        """
        if t <= const.EPSILON or t >= 1.0:
            return (self, None)
        cp0, cp1, p, cp2, cp3 = self.controlpoints_at(t)
#         p.svg_plot(color='#ff0000') #DEBUG: shows inflection points...
        curve1 = CubicBezier(self.p1, cp0, cp1, p)
        curve2 = CubicBezier(p, cp2, cp3, self.p2)
        return (curve1, curve2)

    def subdivide_inflections(self):
        """Subdivide this curve at the inflection points, if any.
        Returns:
            A list containing one to three curves depending on whether
            there are no inflections, one inflection, or two inflections.
        """
        t1, t2 = self.find_inflections()
        if t1 > 0.0 and t2 == 0.0:
            return self.subdivide(t1)
        elif t1 == 0.0 and t2 > 0.0:
            return self.subdivide(t2)
        elif t1 > 0.0 and t2 > 0.0:
            curves = []
            curve1, curve2 = self.subdivide(t1)
            # Two inflection points
            t1, t2 = curve1.find_inflections()
            t = max(t1, t2)
            if t > 0.0:
                curves.extend(curve1.subdivide(t))
                curves.append(curve2)
            else:
                t1, t2 = curve1.find_inflections()
                t = max(t1, t2)
                if t > 0.0:
                    curves.append(curve1)
                    curves.extend(curve2.subdivide(t))
                else:
                    curves.extend((curve1, curve2))
            #curves[0].svg_plot()
            #curves[1].svg_plot()
            #curves[2].svg_plot()
            return curves
        else:
            return [self,]

    def controlpoints_at(self, t):
        """Get the point on this curve corresponding to `t`
        plus control points.

        Relevant points found using De Casteljaus's algorithm. Useful for
        subdividing the curve at `t`.

        Args:
            t: location on curve. A value between 0.0 and 1.0

        Returns:
            A tuple of the form (C0, C1, P, C2, C3) where C1 and C2 are
            the control points tangent to P and C0 and C3 would be the
            new control points of the endpoints where this curve to be
            subdivided at P.
        """
        # First intermediate points
        d01 = (1. - t) * self.p1 + t * self.c1
        d12 = (1. - t) * self.c1 + t * self.c2
        d23 = (1. - t) * self.c2 + t * self.p2
        # Second intermediate points
        d012 = (1. - t) * d01 + t * d12
        d123 = (1. - t) * d12 + t * d23
        # Finally, the split point
        d0123 = (1. - t) * d012 + t * d123

        return (d01, d012, d0123, d123, d23)

    def derivative1(self, t):
        """Calculate the 1st derivative of this curve at `t`.

        Returns:
            The first derivative at `t` as 2-tuple (dx, dy).
        """
        t2 = t**2
        return (self.p1 * ((2 * t - t2 - 1) * 3) +
                self.c1 * ((3 * t2 - 4 * t + 1) * 3) +
                self.c2 * (t * (2 - 3 * t) * 3) +
                self.p2 * (t2 * 3) )

    def derivative2(self, t):
        """Calculate the 2nd derivative of this curve at `t`.

        Returns:
            The second derivative at `t` as 2-tuple (dx, dy).
        """
        return 6 * ( (1 - t) * self.p1 + (3*t - 2) * self.c1 +
                     (1 - 3*t) * self.c2 + t * self.p2 )

    def curvature(self, t):
        """Calculate the curvature at `t`.

        See http://www.spaceroots.org/documents/ellipse/node6.html

        Returns:
            A scalar value `K` representing the curvature at `t`.
            Negative if curving to the right or positive
            if curving to the left when `t` increases.
        """
        d1 = self.derivative1(t)
        d2 = self.derivative2(t)
        c = (((d1.x * d2.y) - (d1.y * d2.x)) /
             math.pow((d1.x * d1.x) + (d1.y * d1.y), 3./2))
        return c

    def find_inflections(self):
        """Find (t1, t2) where the curve has C1 discontinuities
        (ie from convex to concave or vice versa, or a cusp, or a loop).
        There may be none, one, or two inflections on the curve.

        See http://www.caffeineowl.com/graphics/2d/vectorial/cubic-inflexion.html

        Returns:
            A tuple containing the inflection locations.
            The location values will be 0 if no inflection.
        """
        # Basically the equation to be solved is
        # P' * P'' = 0
        # Where P' and P'' are the first and second derivatives respectively

        # Temporary vectors to simplify the math
        v1 = self.c1 - self.p1

        # First check for a case where the curve is exactly
        # symmetrical along the axis defined by the endpoints.
        # In which case the inflection point is the midpoint.
        # This case is not handled correctly by the normal method.
        # TODO: this fix seems a little funky...
        if v1 == -(self.c2 - self.p2):
            return (0.5, 0.0)

        v2 = self.c2 - self.c1 - v1
        v3 = self.p2 - self.c2 - v1 - 2*v2

        # Calculate quadratic coefficients
        # of the form a*x**2 + b*x + c = 0
        a = v2.x * v3.y - v2.y * v3.x
        b = v1.x * v3.y - v1.y * v3.x
        c = v1.x * v2.y - v1.y * v2.x
#        logger.debug('a=%f, b=%f, c=%f' % (a, b, c))

        # Get the two roots of the quadratic - if any.
        # These will be the inflection locations.
        t1 = 0.0
        t2 = 0.0
        aa = 2 * a
        if abs(aa) > 0.0: # Avoid div by zero
            # the discriminant of the quadratic eq.
            dis = math.sqrt(abs(b*b - 4*a*c))
            t1 = (-b - dis) / aa
            t2 = (-b + dis) / aa
#            logger.debug('t1=%f, t2=%f' % (t1, t2))

            if t1 < const.EPSILON or t1 >= (1.0 - const.EPSILON):
                t1 = 0.0
            if t2 < const.EPSILON or t2 >= (1.0 - const.EPSILON):
                t2 = 0.0

        return (t1, t2)

    def length(self, tolerance=None):
        """Calculate the approximate arc length of this curve
        within the specified tolerance.
        The resulting computed arc length will be
        cached so that subsequent calls are not expensive.

        Uses a simple and clever numerical algorithm described/invented by
        Jens Gravesen.

        See:
            http://steve.hollasch.net/cgindex/curves/cbezarclen.html

        Args:
            tolerance: The approximation tolerance.
                Default is const.EPSILON.

        Returns:
            The approximate arc length of this curve.
        """
        if tolerance is None:
            tolerance = const.EPSILON
        # Algorithm:
        #
        # If you denote the length of the
        # control polygon by L1 i.e.:
        #         L1 = |P0 P1| +|P1 P2| +|P2 P3|
        # and the length of the cord by L0 i.e.:
        #         L0 = |P0 P3|
        # then
        #         L = 1/2*L0 + 1/2*L1
        # is a good approximation of the length of the curve,
        # and the difference (L1-L0) is a measure of the error.
        # If the error is too large, then you just subdivide
        # the curve at parameter value 1/2, and find the length of each half.
        if not hasattr(self, '_arc_length'):
            L1 = (self.p1.distance(self.c1) +
                  self.c1.distance(self.c2) +
                  self.c2.distance(self.p2))
            L0 = self.p1.distance(self.p2)
            if L1 - L0 > tolerance:
                # Subdivide the curve and recursively compute the sum.
                b1, b2 = self.subdivide(0.5)
                len1 = b1.length(tolerance=tolerance)
                len2 = b2.length(tolerance=tolerance)
                self._arc_length = len1 + len2
            else:
                self._arc_length = 0.5 * L0 + 0.5 * L1
        return self._arc_length

    def biarc_approximation(self, tolerance=0.01, max_depth=4,
                            line_flatness=0.01, _recurs_depth=0):
        """Approximate this curve using biarcs.

        This will recursively subdivide the curve into a series of
        G1 (tangential continuity) connected arcs or lines until the
        Hausdorff distance between the approximation and this bezier
        curve is within the specified tolerance.

        Args:
            tolerance: Approximation tolerance. A lower value increases
                accuracy at the cost of time and number of generated
                biarc segments.
            max_depth: Maximum recursion depth. This limits how many times
                the Bezier curve can be subdivided.
            line_flatness: Segments flatter than this value will be converted
                to straight line segments instead of arcs with huge radii.
                Generally this should be a small value (say <= 0.01) to avoid
                path distortions.

        Returns:
            A list of Arc and/or Line objects. The list will be empty
            if the curve is degenerate (i.e. if the end points
            are coincident).
        """
#        self.svg_plot(color='#ff0000') #DEBUG
        # Check for degenerate cases:
        # Bail if the curve endpoints are coincident.
        if self.p1 == self.p2:
            return []
        # Or if the curve is basically a straight line then return a Line.
        if self.is_straight_line(line_flatness):
#             logger.debug('curve->line: flatness=%f' % self.flatness())
            return [Line(self.p1, self.p2),]

        if _recurs_depth == 0:
            # Subdivide this curve at any inflection points to make sure
            # the curve has monotone curvature with no discontinuities.
            # Recursively approximate each sub-curve.
            # This should only be required once.
            curves = self.subdivide_inflections()
            if len(curves) > 1:
#                 logger.debug('found inflections - subdividing %d' % len(curves))
                biarcs = []
                for curve in curves:
                    sub_biarcs = curve.biarc_approximation(
                                    tolerance=tolerance, max_depth=max_depth,
                                    line_flatness=line_flatness,
                                    _recurs_depth=_recurs_depth+1)
                    biarcs.extend(sub_biarcs)
                return biarcs

        # Calculate the arc that intersects the two endpoints of this curve
        # and the set of possible biarc joints.
        j_arc = self.biarc_joint_arc()
#         j_arc.svg_plot(color='#c00000') #DEBUG
        # Another degenerate case which shouldn't happen if the line flatness
        # is reasonable.
        if (j_arc is None or j_arc.radius < const.EPSILON or
            j_arc.length() < const.EPSILON):
            return []

        # TODO: Use a better method of finding J.
        # A possibly more accurate method (see A. Riskus, 2006)
        # is to find the intersection of the joint arc and this curve
        # and use that point for J. The curve subdivision would occur at J
        # as well.
        # To make this simple for now:
        # The biarc joint J will be the intersection of the line
        # whose endpoints are the center of the joint arc and the
        # 'middle' (t=0.5) of the bezier curve and the joint arc.
        p = self.point_at(0.5)
        v = p - j_arc.center
        pjoint = v * (j_arc.radius / v.length()) + j_arc.center
#         pjoint.svg_plot(color='#ffff00') #DEBUG

        # Create the two arcs that define the biarc. If one of the curve
        # control points are coincident with the corresponding end point
        # then just make a single arc.
        arc2 = None
        if self.p1 == self.c1:
            arc1 = Arc.from_two_points_and_tangent(self.p2, self.c2,
                                                        self.p1, reverse=True)
        elif self.p2 == self.c2:
            arc1 = Arc.from_two_points_and_tangent(self.p1, self.c1,
                                                        self.p2)
        else:
            arc1 = Arc.from_two_points_and_tangent(self.p1, self.c1,
                                                        pjoint)
            arc2 = Arc.from_two_points_and_tangent(self.p2, self.c2,
                                                        pjoint, reverse=True)

        if _recurs_depth < max_depth:
            # Calculate Hausdorff distance from arcs to this curve
            d1 = self.distance_to_arc(arc1)
            d2 = 0.0 if arc2 is None else self.distance_to_arc(arc2)
            hd = max(d1, d2)
            # If distance is above tolerance then split this curve and
            # recursively approximate the two sub-curves.
            if hd > tolerance:
                curve1, curve2 = self.subdivide(0.5)
                biarcs = curve1.biarc_approximation(tolerance=tolerance,
                                                max_depth=max_depth,
                                                line_flatness=line_flatness,
                                                _recurs_depth=_recurs_depth+1)
                biarcs.extend(curve2.biarc_approximation(tolerance=tolerance,
                                                max_depth=max_depth,
                                                line_flatness=line_flatness,
                                                _recurs_depth=_recurs_depth+1))
                return biarcs
        return [arc1,] if arc2 is None else [arc1, arc2]

    def biarc_joint_arc(self):
        """Calculate the arc that intersects the two endpoints of this curve
        and the set of possible biarc joints.

        Returns:
            The biarc joint arc or None if one can't be computed.
        """
        # The center <s> of the circle is the intersection of the bisectors
        # of line segments P1->P2 and (P1+unit(C1))->(P2+unit(C2))
        chord = Line(self.p1, self.p2)
#        chord.svg_plot()
        u1 = (self.c1 - self.p1).unit()
        u2 = (self.c2 - self.p2).unit()
        useg = Line(self.p1 + u1, self.p2 + P(-u2.x, -u2.y))
#        useg.svg_plot()
        center = chord.bisector().intersection(useg.bisector())
        if center is not None:
            radius = center.distance(self.p1)
            angle = center.angle2(self.p1, self.p2)
            return Arc(self.p1, self.p2, radius, angle, center)
        else:
            return None

    def distance_to_arc(self, arc, ndiv=9):
        """Calculate an approximate normal distance between this curve and
        the specified circular arc.

        The approximation accuracy depends on the number of curve subdivisions
        specified by `ndiv`.
        """
        # TODO: improve this method... Possibilities include using
        # Newton-Raphson to find maximum of the cubic curve, or
        # maybe improve the existing naive method with a binary search.
        dmax = 0.0
        for i in range(ndiv+1):
            t = float(i) / ndiv
            p = self.point_at(t)
#            p.svg_plot('#00cccc') #DEBUG
            d = arc.distance_to_point(p)
            if d > 0.0: # only if arc intersects segment(center,p)
                dmax = max(dmax, d)
        return dmax

    def reversed(self):
        """Return a CubicBezier with control points (direction) reversed."""
        return CubicBezier(self.p2, self.c2, self.p1, self.c1)

    def __str__(self):
        """Concise string representation."""
        return 'CubicBezier((%.4f, %.4f), (%.4f, %.4f), (%.4f, %.4f), (%.4f, %.4f))' % \
                (self.p1.x, self.p1.y, self.c1.x, self.c1.y,
                 self.c2.x, self.c2.y, self.p2.x, self.p2.y)

    def __repr__(self):
        """Precise string representation."""
        return 'CubicBezier((%r, %r), (%r, %r), (%r, %r), (%r, %r))' % \
                (self.p1.x, self.p1.y, self.c1.x, self.c1.y,
                 self.c2.x, self.c2.y, self.p2.x, self.p2.y)

    def to_svg_path(self):
        """Return a string with the SVG path 'd' attribute value
        that corresponds with this curve.
        """
        return ('M %f %f C %f %f %f %f %f %f' %
                (self.p1.x, self.p1.y, self.c1.x, self.c1.y,
                 self.c2.x, self.c2.y, self.p2.x, self.p2.y))


def bezier_circle(center=(0,0), radius=1.0):
    """Create an approximation of a circle with a cubic Bezier curve.

    Args:
        center: The center point of the circle. Default is (0,0).
        radius: The radius of the circle. Default is 1.

    Returns:
        A tuple with four bezier curves for each circle quadrant.
        Circle will be counterclockwise from the positive x axis
        relative to the center point.

    See:
        https://pomax.github.io/bezierinfo/#circles_cubic
    """
    # Magic number for control point tangent length
    k = 0.5522847498308 * radius
    b1 = CubicBezier(P(radius, 0.0) + center,
                     P(radius, k) + center,
                     P(k, radius) + center,
                     P(0.0, radius) + center)
    b2 = CubicBezier(P(0.0, radius) + center,
                     P(-k, radius) + center,
                     P(-radius, k) + center,
                     P(-radius, 0.0) + center)
    b3 = CubicBezier(P(-radius, 0.0) + center,
                     P(-radius, -k) + center,
                     P(-k, -radius) + center,
                     P(0.0, -radius) + center)
    b4 = CubicBezier(P(0.0, -radius) + center,
                     P(k, -radius) + center,
                     P(radius, -k) + center,
                     P(radius, 0.0) + center)
    return (b1, b2, b3, b4)


def bezier_circular_arc(arc):
    """Create a cubic Bezier approximation of a circular arc.
    The central arc must be less than PI/2 radians (90deg).

    Args:
        arc: A geom.Arc

    Returns:
        A CubicBezier.
    """
    #-------------------------------------------------------------------------
    # See: http://itc.ktu.lt/itc354/Riskus354.pdf for possibly
    # better solution.
    # This is from:
    # http://www.spaceroots.org/documents/ellipse/node22.html
    # but specialized for the simpler circular arc case.
    # Implicit derivative of the arc is straightforward.
    # TODO: test this...
    #-------------------------------------------------------------------------
    # Alpha doesn't quite match up with the magic number
    # used for the circle quadrant case and there might be
    # a better approximation...
    N1 = math.tan(arc.angle / 2)
    alpha = math.sin(arc.angle) * ((math.sqrt(4 + (3 * (N1 * N1))) - 1) / 3)
    v1 = arc.p1 - arc.center
    v2 = arc.p2 - arc.center
    c1 = arc.p1 + alpha * P(-v1.y, v1.x)
    c2 = arc.p2 - alpha * P(v2.y, -v2.x)
    return CubicBezier(arc.p1, c1, c2, arc.p2)


def bezier_ellipse(ellipse):
    """Approximate this elliptical arc segment with Bezier curves.

    If the sweep angle is greater than PI/2 the arc will be
    subdivided so that no segment has a sweep angle larger
    than PI/2.

    Args:
        ellipse: An Ellipse or EllipticalArc

    Returns:
        A list containing one to four BezierCurves.
    """
    bz = []
    t1 = getattr(ellipse, 'start_angle', 0.0)
    t2 = t1 + math.pi / 2
    t_end = t1 + getattr(ellipse, 'sweep_angle', math.pi * 2)
    while t2 <= t_end:
        bz.append(bezier_elliptical_arc(ellipse, t1, t2))
        t1 = t2
        t2 += math.pi / 2
    # Create a curve for the remainder
    if t1 < t_end and t2 > t_end:
        bz.append(bezier_elliptical_arc(ellipse, t1, t_end))
    return bz


def bezier_elliptical_arc(ellipse, t1, t2):
    """Compute a BezierCurve that can approximate the
    elliptical arc between `t1` and `t2`.

    This does not subdivide the arc to reduce errors so if
    t2-t1 > PI/2 then the results may be less than ideal.

    Args:
        ellipse: An Ellipse
        t1: Parametric angle from semi-major axis to first location.
        t2: Parametric angle from semi-major axis to second location.

    Returns:
        A cubic bezier curve (as CubicBezier).

    See:
        http://www.spaceroots.org/documents/ellipse/node22.html
    """
    # TODO: test this for arcs in both directions
    sweep_angle = t2 - t1
    N1 = math.tan(sweep_angle / 2)
    alpha = math.sin(sweep_angle) * (math.sqrt(4 + (3 * (N1 * N1))) - 1) / 3
    p1 = ellipse.point_at(t1)
    p2 = ellipse.point_at(t2)
    c1 = p1 + alpha * ellipse.derivative(t1)
    c2 = p2 - alpha * ellipse.derivative(t2)
    return CubicBezier(p1, c1, c2, p2)


def bezier_sine_wave(amplitude, wavelength, cycles=1, origin=(0.0,0.0)):
    """Create an approximation of a sine wave using a cubic Bezier curve.

    Args:
        amplitude: The amplitude (vertical scale) of the sine wave.
            This is one half the vertical distance from the trough to
            the peak.
        wavelength: The horizontal length of one complete cycle.
        cycles: The number of cycles. Default is one.
        origin: Location of start point as a tuple (x,y).
            Default is (0, 0).

    Returns:
        A list of BezierCurve instances that describe the sine wave.
        Each curve will be one quarter of a sine wave, so one cycle
        will return a list four BezierCurves, two cycle will be eight, etc...
    """
    # Control points that will match slope of sine wave.
    # These are derived to match sine curvature at
    # boundary points. See http://mathb.in/1447
    # _T0 = (3.0/2.0*math.pi - 3)
    # _T1 = (6.0 - (_T0 * _T0)) / 6.0 #0.5112873299761805
    # P0 = (0.0, 0.0)
    # P1 = (_T1, _T1)
    # P2 = (1.0, 1.0)
    # P3 = (math.pi / 2.0, 1.0)

    # Apparently these constants produce a more accurate
    # sine wave approximation:
    # See: https://stackoverflow.com/questions/13932704/how-to-draw-sine-waves-with-svg-js
    P0 = (0.0, 0.0)
    P1 = (0.512286623256592433, 0.512286623256592433)
    P2 = (1.002313685767898599, 1.0)
    P3 = (1.570796326794896619, 1.0)

    # According to Gernot Hoffmann these numerically derived
    # constants work even better. I couldn't find
    # a reference to numbers with better precision but
    # it may not be required:
#     P0 = (0.0, 0.0)
#     P1 = (0.5600, 0.5600)
#     P2 = (1.0300, 1.0000)
#     P3 = (1.5708, 1.0)

    # Create a Bezier of the first quadrant of the sine wave
    q0 = CubicBezier(P0, P1, P2, P3)
    # Scale to match specified amplitude and wavelength
    t0 = transform2d.matrix_scale((wavelength/4.0)/P3[0], amplitude/P3[1])
    # First quadrant 0 to PI/2
    q0 = q0.transform(t0)
    dx1 = q0.p1.x - q0.c1.x
    dx2 = q0.p2.x - q0.c2.x
    # Second quadrant PI/2 to PI
    q1 = CubicBezier(q0.p2, (q0.p2.x + dx2, q0.c2.y),
                     (q0.p2.x * 2 + dx1, q0.c1.y), (q0.p2.x * 2, 0))
    # Third quadrant PI to 3PI/2
    q2 = CubicBezier(q1.p2, (q1.p2.x - dx1, -q0.c1.y),
                     (q0.p2.x * 3 - dx2, -q0.c2.y), (q0.p2.x * 3, -q0.p2.y))
    # Fourth quadrant 3PI/2 to 2PI
    q3 = CubicBezier(q2.p2, (q2.p2.x + dx2, -q0.c2.y),
                     (q0.p2.x * 4 + dx1, -q0.c1.y), (q0.p2.x * 4, 0))
    sine_path = []
    for i in range(cycles):
        t = transform2d.matrix_translate(wavelength * i + origin[0], origin[1])
        sine_path.append(q0.transform(t))
        sine_path.append(q1.transform(t))
        sine_path.append(q2.transform(t))
        sine_path.append(q3.transform(t))
    return sine_path


def smoothing_curve(seg1, seg2, cp1=None, smoothness=0.5, match_arcs=True):
    """Create a smoothing Bezier curve between two segments
    that are not currently G1 continuous. The resulting Bezier
    curve will connect the two endpoints of the first segment.

    Args:
        seg1: First path segment containing first and second points.
            Can be a geom.Line or geom.Arc.
        seg2: Second path segment containing second and third points.
            Can be a geom.Line or geom.Arc.
        cp1: First control point computed from previous invocation.
            If cp1 is None then the first endpoint of the first
            segment will be used as the initial control point.
            Default is None.
        smoothness: Affects the magnitude of the smoothing curve
            control points. A value between 0 and 1.
            Default is 0.5
        match_arcs: Try to better match arc connections.

    Returns:
        A tuple containing CubicBezier and the control point
        for the next curve.

    See:
        Maxim Shemanarev
        http://www.antigrain.com/agg_research/bezier_interpolation.html
        http://hansmuller-flex.blogspot.com/2011/04/approximating-circular-arc-with-cubic.html
    """
    # Control point magnitude scaling adjustment constants.
    #-----------------------------------------------------
    # Line->line control point scaling adjustment. See Shemanarev.
    K = 1.2 * smoothness
    # Magic scaling number for arc->bezier control point magnitude
    K_ARC = 0.5522847498308
    # Control point adjustments for arc cusps
    KP1 = 1.5 # First control point magnitude scale adjustment
    KP2 = 0.5 # Second control point magnitude scale adjustment

    p1 = seg1.p1
    p2 = seg1.p2
    # If this is the start of a path then the first control
    # point is the same as the first point.
    if cp1 is None:
        cp1 = p1
    if seg2 is None:
        # seg1 is last segment on a path so create
        # a terminating bezier from quadratic parameters.
        curve = CubicBezier.from_quadratic(p1, cp1, p2)
        return (curve, p2)
    # Line segment connecting the midpoints of the two path segments.
    seg1_len = seg1.length()
    seg_ratio = seg1_len / (seg1_len + seg2.length())
    line_midp = Line(seg1.midpoint(), seg2.midpoint())
    # TODO: Handle CubicBezier curve segments.
    # Calculate magnitude of second control point
    if match_arcs and isinstance(seg1, Arc):
        cp2_mag = seg1.radius * math.tan(abs(seg1.angle) / 2) * K_ARC
        # Determine if there is a winding change.
        line_p1p3 = Line(p1, seg2.p2)
        if ((seg1.is_clockwise() and line_p1p3.which_side(p2) < 0)
                or (not seg1.is_clockwise() and line_p1p3.which_side(p2) > 0)):
            # Adjust control points to better match arcs on cusps
            cp1 = p1 + ((cp1 - p1) * KP1)
            cp2_mag *= KP2
    else:
        cp2_mag = seg_ratio * line_midp.length() * K
    # Magnitude of next first control point
    if match_arcs and isinstance(seg2, Arc):
        cp1_next_mag = seg2.radius * math.tan(abs(seg2.angle) / 2) * K_ARC
    else:
        cp1_next_mag = (1.0 - seg_ratio) * line_midp.length() * K
    # Control point angle
    cp_angle = line_midp.angle()
    # Second control point
    cp2 = p2 + P.from_polar(cp2_mag, cp_angle + math.pi)
    # First control point of the next curve (2nd segment)
    cp1_next = p2 + P.from_polar(cp1_next_mag, cp_angle)
    # seg1 is first segment on a path?
    if cp1 == p1:
        if isinstance(seg1, Arc):
            # TODO: Use circular arc->bezier for first control point.
            arc_curve = bezier_circular_arc(seg1)
            curve = CubicBezier(p1, arc_curve.c1, cp2, p2)
        else:
            # create a starting bezier from quadratic parameters.
            curve = CubicBezier.from_quadratic(p1, cp2, p2)
    else:
        curve = CubicBezier(p1, cp1, cp2, p2)
    return (curve, cp1_next)


