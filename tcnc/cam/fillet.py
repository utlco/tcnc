#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
Connect Line/Arc segments with a fillet arc.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

# import logging

import geom

from geom import fillet


def fillet_path(path, radius, fillet_close=True,
                adjust_rotation=False, mark_fillet=False):
    """Attempt to insert a circular arc of the specified radius
    to blend adjacent path segments that have C0 or G0 continuity.

    Args:
        path: a list of geom.Line or geom.Arc segments.
        fillet_close: If True and the path is closed then
            add a terminating fillet. Default is False.
        adjust_rotation: If True adjust the A axis rotation hints
            to compensate for the offset caused by the fillet.
        mark_fillets: If True add an attribute to the fillet arc
            to mark it to ignore G1. Default is False.

    Returns:
        A new path with fillet arcs. If no fillets are created then
        the original path will be returned.
    """
    if radius < geom.const.EPSILON or len(path) < 2:
        return path
    new_path = []
    seg1 = path[0]
    for seg2 in path[1:]:
        new_segs = create_adjusted_fillet(seg1, seg2, radius,
                                          adjust_rotation=adjust_rotation,
                                          mark_fillet=mark_fillet)
        if new_segs:
            new_path.extend(new_segs[:-1])
            seg2 = new_segs[-1]
        else:
            new_path.append(seg1)
        seg1 = seg2
    new_path.append(seg1)
    # Close the path with a fillet
    if fillet_close and len(path) > 2 and path[0].p1 == path[-1].p2:
        new_segs = create_adjusted_fillet(new_path[-1], new_path[0], radius,
                                          adjust_rotation=adjust_rotation,
                                          mark_fillet=mark_fillet)
        if new_segs:
            new_path[-1] = new_segs[0]
            new_path.append(new_segs[1])
            new_path[0] = new_segs[2]
    # Discard the path copy if no fillets were created...
    return new_path if len(new_path) > len(path) else path


def create_adjusted_fillet(seg1, seg2, radius,
                           adjust_rotation=False, mark_fillet=False):
    """Try to create a fillet between two segments.
    Any GCode rendering hints attached to the segments will
    be preserved.

    Args:
        seg1: First segment, an Arc or a Line.
        seg2: Second segment, an Arc or a Line.
        radius: Fillet radius.
        adjust_rotation: If True adjust the A axis rotation hints
            to compensate for the offset caused by the fillet.
        mark_fillets: If True add an attribute to the fillet arc
            to mark it to ignore G1. Default is False.

    Returns:
        A tuple containing the adjusted segments and fillet arc:
        (seg1, fillet_arc, seg2)
        Returns an empty tuple if the segments cannot be connected
        with a fillet arc (either they are too small, already G1
        continuous, or are somehow degenerate.)
    """
    if geom.segments_are_g1(seg1, seg2):
        return ()
    farc = fillet.create_fillet_arc(seg1, seg2, radius)
    if farc is None:
        return ()
    if mark_fillet:
        farc.ignore_g1 = True # Mark fillet as connecting two non-G1 segments
    if adjust_rotation:
        _adjust_fillet_rotation_hints(seg1, farc, seg2)
    new_segs = fillet.connect_fillet(seg1, farc, seg2)
    _copy_segment_attrs(seg1, new_segs[0])
    _copy_segment_attrs(seg2, new_segs[2])
    return new_segs


def _adjust_fillet_rotation_hints(seg1, farc, seg2):
    """Adjust the A axis rotation hints to compensate for
    the offset caused by a fillet arc.
    """
    a1 = getattr(seg1, 'inline_start_angle', seg1.start_tangent_angle())
    a2 = getattr(seg1, 'inline_end_angle', seg1.end_tangent_angle())
    mu = 1.0 - seg1.mu(farc.p1)
    offset_angle = geom.calc_rotation(a1, a2) * mu
    if not geom.is_zero(offset_angle):
        seg1.inline_end_angle = a2 - offset_angle
        farc.inline_start_angle = seg1.inline_end_angle
    else:
        farc.inline_start_angle = a2
    a1 = getattr(seg2, 'inline_start_angle', seg2.start_tangent_angle())
    a2 = getattr(seg2, 'inline_end_angle', seg2.end_tangent_angle())
    mu = seg2.mu(farc.p2)
    offset_angle = geom.calc_rotation(a1, a2) * mu
    if not geom.is_zero(offset_angle):
        seg2.inline_start_angle = a1 + offset_angle
        farc.inline_end_angle = seg2.inline_start_angle
    else:
        farc.inline_end_angle = a1


def _copy_segment_attrs(seg1, seg2):
    """Copy inline GCode rendering hints from seg1 to seg2."""
    for name in vars(seg1):
        if name.startswith('inline_'):
            setattr(seg2, name, getattr(seg1, name))

