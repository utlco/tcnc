#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
Commonly used constants used in the geometry package.

The following read-only constants are defined:

    EPSILON: A small floating point value which is the maximum
        numeric distance between two floating point numbers for
        them to be considered equal.
    EPSILON_PRECISION: The number of digits after the decimal point of
        EPSILON.
    EPSILON_FLOAT_FMT: A format string for displaying numbers that
        have PRECISION number of digits after the decimal point.

The tolerance value (EPSILON) `must` be set once (and only once) before
using the geometry package. This is enforced.

Useful values are small numbers in the range of 1e-09 to 1e-05. It depends
on the application and the size of numbers used with the package.

If set_epsilon() is not called by the user then a default value will
be set the first time the EPSILON attribute is accessed.
It cannot then be modified.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import math

#: Commonly used constant PI*2
TAU = math.pi * 2

#: Tolerance value used for floating point comparisons
EPSILON = 1e-06
#: Handy for comparing distance**2 when avoiding sqrt
EPSILON2 = EPSILON * EPSILON
#: Number of digits after decimal point
EPSILON_PRECISION = 6
#: Format string for float values that matches precision
EPSILON_FLOAT_FMT = '%.6f'


def set_epsilon(value):
    """Set the global absolute error tolerance value and rounding limit for
    approximate floating point comparison operations.
    This value is accessible via the geom.EPSILON global variable.

    The default value of 1e-06 is suitable for values
    that are in the 'countable range'. You may need a larger
    epsilon when using large absolute values, and a smaller value
    for very small values close to zero. Otherwise approximate
    comparison operations may not behave as expected.

    In general, this should be called only once before using
    any modules that refer to EPSILON.

    Args:
        value: Float tolerance value.
    """
    #pylint: disable=global-statement
    global EPSILON, EPSILON2, EPSILON_PRECISION, EPSILON_FLOAT_FMT
    # Tolerance value
    EPSILON = float(value)
    EPSILON2 = EPSILON * EPSILON
    # Number of digits after decimal point
    EPSILON_PRECISION = max(0, int(round(abs(math.log(value, 10)))))
    # Format string for float values that matches precision
    EPSILON_FLOAT_FMT = '%%.%df' % EPSILON_PRECISION


def float_eq(value1, value2):
    """Compare two floats for equality.
    The two float are considered equal if the difference between them is
    less than EPSILON.

    For a discussion of floating point comparisons see:
        http://randomascii.wordpress.com/2012/02/25/comparing-floating-point-numbers-2012-edition/

    Args:
        value1: Float value
        value2: Float value

    Returns:
        True if the two values are approximately equal.
    """
    # This method tries to behave better when comparing small numbers:
    #
#     norm = max(abs(a), abs(b))
#     return (norm < EPSILON) or (abs(a - b) < (EPSILON * norm))
    #
    # This simpler and faster version works fine in practice:
    #
    return abs(value1 - value2) < EPSILON


def is_zero(value):
    """Determine if the float value is essentially zero.

    A shortcut for float_eq(n, 0.0).
    """
    return -EPSILON < value < EPSILON


def float_round(value):
    """Round the value to a rounding precision corresponding to EPSILON.
    """
    return round(value, EPSILON_PRECISION)


# This replaces the above symbols if the enforcement of EPSILON
# usage is important. This comes at the expense of runtime speed.
# It also causes pylint to freak out.
# Uncomment all this to enforce EPSILON usage:
# import sys
#
# class _Epsilon(object):
#     """This pattern is courtesy Alex Martelli:
#     https://www.safaribooksonline.com/library/view/python-cookbook/0596001673/ch05s16.html
#
#     This will ensure that EPSILON is bound only once at runtime.
#     """
#     class ConstError(TypeError):
#         """Raised if EPSILON is modified more than once."""
#         pass
#
#     _DEFAULT_EPSILON = 1e-06
#
#     def set_epsilon(self, value):
#         """Replaces module function."""
#         # The math module needs to be imported here so that it is
#         # reachable when the module namespace is replaced.
#         import math
#         self.EPSILON = float(value)
#         self.EPSILON_PRECISION = max(0, int(round(abs(math.log(value, 10)))))
#         self.EPSILON_FLOAT_FMT = '%%.%df' % self.EPSILON_PRECISION
#
#     def float_eq(self, value1, value2):
#         """Replaces module function."""
#         return abs(value1 - value2) < self.EPSILON
#
#     def is_zero(self, value):
#         """Replaces module function."""
#         return -self.EPSILON < value < self.EPSILON
#
#     def float_round(self, value):
#         """Replaces module function."""
#         return round(value, self.EPSILON_PRECISION)
#
#     def __setattr__(self, name, value):
#         if self.__dict__.has_key(name):
#             raise self.ConstError, "Can't rebind const(%s)" % name
#         self.__dict__[name] = value
#
#     def __delattr__(self, name):
#         if self.__dict__.has_key(name):
#             raise self.ConstError, "Can't unbind const(%s)" % name
#         raise NameError, name
#
#     def __getattr__(self, name):
#         if not self.__dict__.has_key(name) and name == 'EPSILON':
#             # Set defaults if set_epsilon() has not already been invoked.
#             self.set_epsilon(self._DEFAULT_EPSILON)
#         return self.__dict__[name]
#
#
# _epsilon = _Epsilon()
# sys.modules[__name__] = _epsilon

