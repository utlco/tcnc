#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import logging

import geom

logger = logging.getLogger(__name__)


def split_path_g1(path):
    """Split the path at path vertices that connect
    non-tangential segments.

    Args:
        path: The path to split.

    Returns:
        A list of one or more paths.
    """
    path_list = []
    new_path = []
    seg1 = path[0]
    for seg2 in path[1:]:
        new_path.append(seg1)
        if (not geom.float_eq(seg1.end_tangent_angle(),
                             seg2.start_tangent_angle()) or
            hasattr(seg1, 'ignore_g1') or hasattr(seg2, 'ignore_g1')):
            path_list.append(new_path)
            new_path = []
        seg1 = seg2
    new_path.append(seg1)
    path_list.append(new_path)
    return path_list


def inline_hint_attrs(segment):
    """Generator to get hint attribute names."""
    for name in vars(segment):
        if name.startswith('inline_'):
            yield name


def copy_segment_attrs(seg1, seg2):
    """Copy inline GCode rendering hints from seg1 to seg2."""
    for name in inline_hint_attrs(seg1):
        setattr(seg2, name, getattr(seg1, name))


def seg_start_angle(segment):
    """The tangent angle of this segment at the first end point.
    If there is a cam segment hint attribute ('inline_start_angle')
    its value will be returned instead."""
    return getattr(segment, 'inline_start_angle', segment.start_tangent_angle())

def seg_end_angle(segment):
    """The tangent angle of this segment at the last end point.
    If there is a cam segment hint  attribute ('inline_end_angle')
    its value will be returned instead."""
    return getattr(segment, 'inline_end_angle', segment.end_tangent_angle())

