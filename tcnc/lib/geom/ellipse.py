#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""Two dimensional ellipse and elliptical arc.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import math
import logging
logger = logging.getLogger(__name__)

from . import const

from .point import P
from .line import Line


class Ellipse(object):
    """Two dimensional ellipse.

    For the parametric function the parameter `t` is the
    parametric angle (aka eccentric anomaly) from
    the semi-major axis of the ellipse before stretch and rotation
    (i.e. as if this ellipse were a circle.)

    The ellipse will be normalized so that the semi-major axis
    is aligned with the X axis (i.e. `rx` >= `ry`.) The ellipse
    rotation (phi) will be adjusted 90deg to compensate if
    necessary.

    See:
        https://en.wikipedia.org/wiki/Ellipse
        http://www.spaceroots.org/documents/ellipse/
        http://www.w3.org/TR/SVG11/implnote.html#ArcImplementationNotes
        https://en.wikipedia.org/wiki/Eccentric_anomaly
    """
    def __init__(self, center, rx, ry=None, phi=0.0):
        """
        Args:
            center: The center of the ellipse.
            rx: Semi-major axis length.
            ry: Semi-minor axis length. Default is :param:`rx` if None.
            phi: Rotation angle of the ellipse.
        """
        self.center = P(center)
        rx = abs(rx)
        if ry is None:
            ry = rx
        else:
            ry = abs(ry)
        if const.float_eq(rx, ry):
            self.phi = 0.0
        elif rx < ry:
            # Rotate to normalize
            self.phi = (phi + math.pi / 2)
        else:
            self.phi = phi
        # Normalize axes
        self.rx = max(rx, ry)
        self.ry = min(rx, ry)

    def is_circle(self):
        return const.float_eq(self.rx, self.ry)

    def theta2t(self, theta):
        """Compute parametric angle from geometric angle.

        Args:
            theta: The geometrical angle from
                the semi-major axis and a point on the ellipse.

        Returns:
            `t` - the parametric angle - 0 < `t` < 2*PI.
        """
        if self.is_circle():
            return theta
        else:
            return math.atan2(math.sin(theta)/self.ry, math.cos(theta)/self.rx)

    def pointt(self, p):
        """Compute `t` given a point on the ellipse.

        Args:
            p: A point on the ellipse.

        Returns:
            `t` - the parametric angle - 0 < `t` < 2*PI.
        """
        theta = self.center.angle2(self.point_at(0), p)
        return self.theta2t(theta)

    def point_at(self, t):
        """Return the point on the ellipse at `t`.

        This is the parametric function for this ellipse.

        Args:
            t: Parametric angle - 0 < t < 2*PI.

        Returns:
            A point at :param:`t`
        """
        cos_theta = math.cos(self.phi)
        sin_theta = math.sin(self.phi)
        cos_t = math.cos(t)
        sin_t = math.sin(t)
        x = (self.rx * cos_theta * cos_t) - (self.ry * sin_theta * sin_t)
        y = (self.rx * sin_theta * cos_t) + (self.ry * cos_theta * sin_t)
        return self.center + (x, y)

    def point_inside(self, p):
        """Test if point is inside ellipse or not.

        Args:
            p: Point (x, y) to test.

        Returns:
            True if the point is inside the ellipse, otherwise False.
        """
        if self.is_circle() or const.is_zero(self.phi):
            x, y = (P(p) - self.center)
        else:
            # Canonicalize the point by rotating it back clockwise by phi
            x, y = (P(p) - self.center).rotate(-self.phi)
        # Point is inside if the result sign is negative
        xrx = x / self.rx
        yry = y / self.ry
        return ((xrx * xrx) + (yry * yry) - 1) < 0

    def all_points_inside(self, points):
        """Return True if all the given points are inside this circle."""
        for p in points:
            if not self.point_inside(p):
                return False
        return True

    def focus(self):
        """The focus of this ellipse.

        Returns:
            Distance from center to focus points.
        """
        return math.sqrt(self.rx*self.rx - self.ry*self.ry)

    def focus_points(self):
        """Return the two focus points.

        Returns:
            A tuple of two focus points along major axis.
        """
        d = self.focus()
        fp = P(d * math.cos(self.phi), d * math.sin(self.phi))
        return (self.center - fp, self.center + fp)

    def area(self):
        """The area of this ellipse."""
        return math.pi * self.rx * self.ry

    def eccentricity(self):
        """The eccentricity `e` of this ellipse."""
        return self.focus() / self.rx

    def curvature(self, p):
        """The curvature at a given point.
        """
        x, y = p
        rx2 = self.rx * self.rx
        ry2 = self.ry * self.ry
        tmp1 = 1 / (rx2 * ry2)
        tmp2 = ((x * x) / (rx2 * rx2)) + ((y * y) / (ry2 * ry2))
        return tmp1 * math.pow(tmp2, -1.5)

    def derivative(self, t, d=1):
        """First and second derivatives of the parametric ellipse function.

        Args:
            t: Parametric angle - 0 < t < 2*PI.
            d: 1 => First derivative, 2 => Second derivative.
                Default is 1.

        Returns:
            A 2-tuple: (dx, dy)
        """
        cos_theta = math.cos(self.phi)
        sin_theta = math.sin(self.phi)
        cos_t = math.cos(t)
        sin_t = math.sin(t)
        if d == 1:
            dx = -(self.rx * cos_theta * sin_t) - (self.ry * sin_theta * cos_t)
            dy = -(self.rx * sin_theta * sin_t) + (self.ry * cos_theta * cos_t)
        else:
            dx = -(self.rx * cos_theta * cos_t) + (self.ry * sin_theta * sin_t)
            dy = -(self.rx * sin_theta * cos_t) - (self.ry * cos_theta * sin_t)
        return P(dx, dy)

    def _init_axes(self, rx, ry, phi):
        """Make sure major and minor axes are not reversed."""
        rx = abs(rx)
        ry = abs(ry)
        if rx < ry:
            self.rx = ry
            self.ry = rx
            self.phi = phi + math.pi/2
        else:
            self.rx = rx
            self.ry = ry
            self.phi = phi


class EllipticalArc(Ellipse):
    """Two dimensional elliptical arc. A section of an ellipse.

    See:
        http://www.w3.org/TR/SVG11/implnote.html#ArcImplementationNotes
    """
    def __init__(self, center, p1, p2, rx, ry,
                 start_angle, sweep_angle,
                 large_arc, sweep_flag, phi=0.0):
        """Create an elliptical arc.
        If only center parameters or endpoint parameters are known
        the static factory methods can be used instead.

        Args:
            p1: The start point of the arc.
            p2: The end point of the arc.
            rx: Semi-major axis length.
            ry: Semi-minor axis length.
            start_angle: Parametric start angle of the arc.
            sweep_angle: Parametric sweep angle of the arc.
            large_arc: The large arc flag.
            sweep_flag: The sweep flag.
            phi: Rotation angle, in radians, of the ellipse. Default is 0.
        """
        self.center = center
        self.p1 = P(p1)
        self.p2 = P(p2)
        self.rx = abs(rx)
        self.ry = abs(ry)
        self.start_angle = start_angle
        self.sweep_angle = sweep_angle
        self.large_arc = large_arc
        self.sweep_flag = sweep_flag
        self.phi = phi

    @staticmethod
    def from_center(center, rx, ry, start_angle, sweep_angle, phi=0.0):
        """Create an elliptical arc from center parameters.

        Args:
            center: The center point of the arc.
            rx: Semi-major axis length.
            ry: Semi-minor axis length.
            start_angle: Start angle of the arc.
            sweep_angle: Sweep angle of the arc.
            phi: The angle from the X axis to the
                semi-major axis of the ellipse.

        Returns:
            An EllipticalArc
        """
        p1 = P(rx * math.cos(start_angle),
                    ry * math.sin(start_angle)) + center
        p2 = P(rx * math.cos(start_angle + sweep_angle),
                    ry * math.sin(start_angle + sweep_angle)) + center
#         mrot = transform2d.matrix_rotate(phi)
#         p1 = p1.transform(mrot)
#         p2 = p2.transform(mrot)
        large_arc = 1 if abs(sweep_angle) > math.pi else 0
        sweep_flag = 1 if sweep_angle > 0.0 else 0
        arc = EllipticalArc(center, p1, p2, rx, ry, start_angle, sweep_angle,
                            large_arc, sweep_flag, phi)
        return arc

    @staticmethod
    def from_endpoints(p1, p2, rx, ry, large_arc, sweep_flag, phi=0.0):
        """Create an elliptical arc from SVG-style endpoint parameters.
        This will correct out of range parameters as per SVG spec.
        The center, start angle, and sweep angle will also be
        calculated.

        See:
            https://www.w3.org/TR/SVG11/implnote.html#ArcSyntax
            https://www.w3.org/TR/SVG11/implnote.html#ArcOutOfRangeParameters

        Args:
            p1: The start point of the arc.
            p2: The end poin of the arc.
            rx: Semi-major axis length.
            ry: Semi-minor axis length.
            large_arc: The large arc flag.
            sweep_flag: The sweep flag.
            phi: The angle in radians from the X axis to the
                semi-major axis of the ellipse. Default is 0.

        Returns:
            An EllipticalArc or None if `rx` or `ry` is 0.
        """
        p1 = P(p1)
        p2 = P(p2)
        # If the semi-major of semi-minor axes are 0 then
        # this should really be a straight line.
        if const.is_zero(rx) or const.is_zero(ry):
            return None
        rx = abs(rx)
        ry = abs(ry)
        # Ensure radii are large enough and correct if not.
        # As per SVG standard section F.6.6.
        xprime, yprime = ((p1 - p2) / 2).rotate(phi)
        zz = (xprime * xprime) / (rx * rx) + (yprime * yprime) / (ry * ry)
        if zz > 1.0:
            logger.debug('Arc radii too small.')
            z = math.sqrt(zz)
            rx = z * rx
            ry = z * ry
        rx2 = rx * rx
        ry2 = ry * ry
        xprime2 = xprime * xprime
        yprime2 = yprime * yprime
        t1 = (rx2 * ry2) - (rx2 * yprime2) - (ry2 * xprime2)
        t2 = (rx2 * yprime2) + (ry2 * xprime2)
        t3 = t1 / t2
#         logger.debug('t1=%f, t2=%f, t3=%f' % (t1, t2, t3))
        t4 = math.sqrt(t3)
        cxprime = t4 * ((rx * yprime) / ry)
        cyprime = t4 * -((ry * xprime) / rx)
        if large_arc == sweep_flag:
            cxprime = -cxprime
            cyprime = -cyprime
        midp = (p1 + p2) / 2
        center = P(cxprime, cyprime).rotate(-phi) + midp
        vx1 = (xprime - cxprime) / rx
        vy1 = (yprime - cyprime) / rx
        vx2 = (-xprime - cxprime) / rx
        vy2 = (-yprime - cyprime) / rx
        origin = P(0.0, 0.0)
        start_angle = origin.angle2((1.0, 0.0), (vx1, vy1))
        sweep_angle = origin.angle2((vx1, vy1), (vx2, vy2))

        arc = EllipticalArc(center, p1, p2, rx, ry, start_angle,
                            sweep_angle, large_arc, sweep_flag, phi)
        return arc

    def transform(self, matrix):
        """Transform this using the specified affine transform matrix.
        """
        # TODO: implement this.
        # See: http://atrey.karlin.mff.cuni.cz/projekty/vrr/doc/man/progman/Elliptic-arcs.html
        raise Exception('not implemented.')


def ellipse_in_parallelogram(vertices, eccentricity=1.0):
    """Inscribe a parallelogram with an ellipse.

    See: Horwitz 2008, http://arxiv.org/abs/0808.0297

    :vertices: The four vertices of a parellelogram as a list of 2-tuples.
    :eccentricity: The eccentricity of the ellipse.
        Where 0.0 >= `eccentricity` <= 1.0.
        If `eccentricity` == 1.0 then a special eccentricity value will
        be calculated to produce an ellipse of maximal area.
        The minimum eccentricity of 0.0 will produce a circle.

    :return: A tuple containing the semi-major and semi-minor axes
        respectively.
    """
    # Determine the angle of the ellipse major axis
    axis = Line(vertices[0], vertices[2])
    major_angle = axis.angle()
    center = axis.midpoint()
    # The parallelogram is defined as having four vertices
    # O = (0,0), P = (l,0), Q = (d,k), R = (l+d,k),
    # where l > 0, k > 0, and d >= 0.
    # Unlike Horwitz, h is used instead of l because it's easier to read.
    # Determine the acute corner angle of the parallelogram.
    theta = abs(P(vertices[0]).angle2(vertices[1], vertices[3]))
    nfirst = 0 # index of first point
    if theta > (math.pi / 2):
        # First corner was obtuse, use the next corner...
        theta = math.pi - theta
        nfirst = 1
        # Rotate the major angle
        major_angle += math.pi / 2
    h2 = P(vertices[nfirst]).distance(vertices[nfirst+1])
    h = P(vertices[nfirst+1]).distance(vertices[nfirst+2])
    k = math.sin(theta) * h2
    d = math.cos(theta) * h2
    # Use a nice default for degenerate eccentricity values
    if eccentricity >= 1.0 or eccentricity < 0.0:
        # This seems to produce an ellipse of maximal area
        # but I don't have proof.
        v = k / 2
    else:
        # Calculate v for minimal eccentricity (a circle)
        v = k / 2 * ((d + h)**2 + k*k) / (k*k + d*d + h*h)
        # Then add the desired eccentricity.
        v *= 1.0 - eccentricity
    A = k**3
    B = k * (d + h)**2 - (4 * d * h * v)
    C = -k * (k*d - 2*h*v + k*h)
    D = -2 * k*k * h * v
    E = 2 * k * h * v * (d - h)
    F = k * h*h * v*v
    T1 = (A*E*E) + (B*D*D) + (4*F*C*C) - (2*C*D*E) - (4*A*B*F)
    T2 = 2 * (A*B - C*C)
    T3 = math.sqrt((B-A)*(B-A) + (4 * C*C))
    # Calculate semi-major axis
    a = math.sqrt(T1 / (T2 * ((A + B) - T3)))
    # Calculate semi-minor axis
    b = math.sqrt(T1 / (T2 * ((A + B) + T3)))
    return Ellipse(center, a, b, major_angle)



def intersect_circle(c1_center, c1_radius, c2_center, c2_radius):
    """The intersection (if any) of two circles.

    See:
        <http://mathworld.wolfram.com/Circle-CircleIntersection.html>

    Args:
        c1_center: Center of first circle.
        c1_radius: Radius of first circle.
        c2_center: Center of second circle.
        c2_radius: Radius of second circle.

    Returns:
        A tuple containing two intersection points if the circles
        intersect. A tuple containing a single point if the circles
        are only tangentially connected. An empty tuple if the circles
        do not intersect or if they are coincident (infinite intersections).
    """
    line_c1c2 = Line(c1_center, c2_center)
    # Distance between the two centers
    dist_c1c2 = line_c1c2.length()
    if dist_c1c2 > (c1_radius + c2_radius):
        # Circles do not intersect.
        return ()
    # Check for degenerate cases
    if const.is_zero(dist_c1c2):
        # Circles are coincident so the number of intersections is infinite.
        return () # For now this means no intersections...
    elif const.float_eq(dist_c1c2, c1_radius + c2_radius):
        # Circles are tangentially connected at a single point.
        return (line_c1c2.midpoint(),)
    # Radii ** 2
    rr1 = c1_radius * c1_radius
    rr2 = c2_radius * c2_radius
    # The distance from circle centers to the radical line
    # This is the X distance from C1 to the intersections.
    dist_c1rad = ((dist_c1c2 * dist_c1c2) - rr2 + rr1) / (2 * dist_c1c2)
    # Half the length of the radical line segment.
    # I.e. half the distance between the two intersections.
    # This is the Y distance from C1 to the intersections.
    half_rad = math.sqrt(rr1 - (dist_c1rad * dist_c1rad))
    # Intersection points
    p1 = c1_center + (dist_c1rad, half_rad)
    p2 = c1_center + (dist_c1rad, -half_rad)
    return (p1, p2)

