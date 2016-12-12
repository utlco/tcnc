#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
2D geometry package.

Parts of this library where inspired by planar, a 2D geometry library for
python gaming:
    https://bitbucket.org/caseman/planar/
"""
#from . import debug

# Expose package-wide constants and functions
from .const import TAU, set_epsilon, is_zero, float_eq, float_round
from .util import normalize_angle, calc_rotation, segments_are_g1

# Expose some basic geometric classes at package level
from .point import P
from .line import Line
from .arc import Arc
from .box import Box
