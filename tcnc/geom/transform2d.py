#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""Basic 2D affine transform matrix operations.
====
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import math


#:2D tranform identity matrix
IDENTITY_MATRIX = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))


def compose_transform(m1, m2):
    """Combine two matrices by multiplying them.

    :param m1: 2X3 2D transform matrix.
    :param m2: 2X3 2D transform matrix.

    Note:
        `m2` is applied before (to) `m1`
    """
    m100 = m1[0][0]
    m101 = m1[0][1]
    m110 = m1[1][0]
    m111 = m1[1][1]
    return ((m100 * m2[0][0] + m101 * m2[1][0],
             m100 * m2[0][1] + m101 * m2[1][1],
             m100 * m2[0][2] + m101 * m2[1][2] + m1[0][2]),
            (m110 * m2[0][0] + m111 * m2[1][0],
             m110 * m2[0][1] + m111 * m2[1][1],
             m110 * m2[0][2] + m111 * m2[1][2] + m1[1][2]))

def matrix_rotate(angle, origin=(0.0, 0.0)):
    """Create a transform matrix to rotate about the origin.

    :param angle: Rotation angle in radians.
    :param origin: Optional rotation origin. Default is (0,0).
    """
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    m1 = ((cos_a, -sin_a, origin[0]), (sin_a, cos_a, origin[1]))
    m2 = matrix_translate(-origin[0], -origin[1])
    return compose_transform(m1, m2)

def matrix_translate(x, y):
    """Create a transform matrix to translate (move).

    :param x: translation along X axis
    :param y: translation along Y axis
    """
    return ((1.0, 0.0, x), (0.0, 1.0, y))

def matrix_scale(scale_x, scale_y, origin=None):
    """Create a transform matrix to scale.

    :param scale_x: X axis scale factor
    :param scale_y: Y axis scale factor
    :param origin: Optional scale origin. Default is (0,0).
    """
    m = ((scale_x, 0.0, 0.0), (0.0, scale_y, 0.0))
    if origin is not None:
        ms1 = matrix_translate(-origin.x, -origin.y)
        ms2 = matrix_translate(origin.x, origin.y)
        m = compose_transform(ms2, compose_transform(m, ms1))
    return m

def matrix_scale_translate(scale_x, scale_y, offset_x, offset_y):
    """Create a transform matrix to scale and translate.

    :param scale_x: X axis scale factor
    :param scale_y: Y axis scale factor
    :param offset_x: translation along X axis
    :param offset_y: translation along Y axis
    """
    return ((scale_x, 0.0, offset_x), (0.0, scale_y, offset_y))

def matrix_skew_x(angle):
    """Create a transform matrix to skew along X axis by `angle`.

    :param angle: Angle in radians to skew.
    """
    return ((1.0, math.tan(angle), 0.0),(0.0, 1.0, 0.0))

def matrix_skew_y(angle):
    """Create a transform matrix to skew along Y axis by `angle`.

    :param angle: Angle in radians to skew.
    """
    return ((1.0, 0.0, 0.0),(math.tan(angle), 1.0, 0.0))

def matrix_apply_to_point(matrix, p):
    """Return a copy of `p` with the transform matrix applied to it."""
    return (matrix[0][0] * p[0] + matrix[0][1] * p[1] + matrix[0][2],
            matrix[1][0] * p[0] + matrix[1][1] * p[1] + matrix[1][2])

def canonicalize_point(p, origin, theta):
    """Canonicalize the point so that the origin is (0, 0)
    and axis rotation is zero.

    This just rotates then translates the point.

    :param p: The point to canonicalize.
    :param origin: The origin offset as a 2-tuple (X, Y).
    :param theta: The axis rotation angle.
    """
    p = matrix_apply_to_point(matrix_rotate(-theta), p)
    return (p[0] - origin[0], p[1] - origin[1])
