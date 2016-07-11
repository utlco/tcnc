#-----------------------------------------------------------------------------#
#    Copyright 2012-2016 Claude Zervas
#    email: claude@utlco.com
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#-----------------------------------------------------------------------------#
"""Basic 2D utility functions.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import math

from . import const

from .const import TAU

# print('importing util')
# def dummy():
#     print('dummy')


def normalize_angle(angle, center=math.pi):
    """Normalize ``angle`` (in radians) about a 2*PI interval centered
    at ``center``.

    For angle between 0 and 2*PI (default):
        normalize_angle(angle, center=math.pi)
    For angle between -PI and PI:
        normalize_angle(angle, center=0.0)

    Args:
        angle: Angle to normalize
        angle: float
        center: Center value about which to normalize.
            Default is math.pi.
        center: float
    """
    return angle - (TAU * math.floor((angle + math.pi - center) / TAU))

def calc_rotation(start_angle, end_angle):
    """Calculate the amount of rotation required to get from
    `start_angle` to `end_angle`.

    Args:
        start_angle: Start angle in radians.
        end_angle: End angle in radians.

    Returns:
        Rotation amount in radians where -PI <= rotation <= PI.
    """
    if const.float_eq(start_angle, end_angle):
        return 0.0
    start_angle = normalize_angle(start_angle, 0)
    end_angle = normalize_angle(end_angle, 0)
    rotation = end_angle - start_angle
    if rotation < -math.pi:
        rotation += TAU
    elif rotation > math.pi:
        rotation -= TAU
    return rotation


def segments_are_g1(seg1, seg2, tolerance=None):
    """Determine if two segments have G1 continuity
    (are tangentially connected.)
    G1 implies G0 continuity.

    Args:
        seg1: First segment. Can be geom.Line, geom.Arc, geom.CubicBezier.
        seg2: Second segment. Can be geom.Line, geom.Arc, geom.CubicBezier.
        tolerance: G0/G1 tolerance. Default is geom.const.EPSILON.

    Returns:
        True if the two segments have G1 continuity within the
        specified tolerance. Otherwise False.
    """
    if tolerance is None:
        tolerance = const.EPSILON
    # G0 continuity - end points are connected
    is_G0 = seg1.p2.almost_equal(seg2.p1, tolerance)
    # G1 continuity - segment end points share tangent
    td = seg1.end_tangent_angle() - seg2.start_tangent_angle()
    is_G1 = abs(td) < tolerance
    return is_G0 and is_G1
