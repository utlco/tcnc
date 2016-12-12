#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
Offset Line/Arc segments in a tool path to compensate for tool trail offset.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import math
# import logging

import geom
from . import toolpath
from . import util

# logger = logging.getLogger(__name__)

def offset_path(path, offset, g1_tolerance=None):
    """Recalculate path to compensate for a trailing tangential offset.
    This will shift all of the segments by `offset` amount. Arcs will
    be recalculated to correct for the shift offset.

    Args:
        path: The path to recalculate.
        offset: The amount of tangential tool trail.

    Returns:
        A new path

    Raises:
        :class:`cam.toolpath.ToolpathException`: if the path contains segment
            types other than Line or Arc.
    """
    if geom.float_eq(offset, 0.0):
        return path;
    offset_path = []
    prev_seg = None
    prev_offset_seg = None
    for seg in path:
        if seg.p1 == seg.p2:
            # Skip zero length segments
            continue
        if isinstance(seg, geom.Line):
            # Line segments are easy - just shift them forward by offset
            offset_seg = seg.shift(offset)
        elif isinstance(seg, geom.Arc):
            offset_seg = offset_arc(seg, offset)
        else:
            raise toolpath.ToolpathException('Unrecognized path segment type.')
        # Fix discontinuities caused by offsetting non-G1 segments
        if prev_seg is not None:
            if prev_offset_seg.p2 != offset_seg.p1:
                if geom.float_eq(prev_offset_seg.end_tangent_angle(),
                                 offset_seg.start_tangent_angle()):
                    # If G1 continuous then just insert a connecting line.
                    connect_seg = geom.Line(prev_offset_seg.p2, offset_seg.p1)
                else:
                    # Insert an arc in tool path to rotate the tool to the next
                    # starting tangent when the segments are not G1 continuous.
                    # TODO: avoid creating tiny segments by extending
                    # offset segment.
                    p1 = prev_offset_seg.p2
                    p2 = offset_seg.p1
                    angle = prev_seg.p2.angle2(p1, p2)
                    connect_seg = geom.Arc(p1, p2, offset, angle, prev_seg.p2)
                connect_seg.inline_start_angle = prev_seg.end_tangent_angle()
                connect_seg.inline_end_angle = seg.start_tangent_angle()
                offset_path.append(connect_seg)
                prev_offset_seg = connect_seg
            elif (geom.segments_are_g1(prev_seg, seg, g1_tolerance) and
                  not hasattr(prev_seg, 'ignore_g1') and
                  not hasattr(seg, 'ignore_g1')):
                # Add hint for smoothing pass
                prev_offset_seg.g1 = True
        prev_seg = seg
        prev_offset_seg = offset_seg
        offset_path.append(offset_seg)
    # Compensate for starting angle
    start_angle = (offset_path[0].p1 - path[0].p1).angle()
    offset_path[0].inline_start_angle = start_angle
    return offset_path


def offset_arc(arc, offset):
    """Offset the arc by the specified offset.
    """
    start_angle = arc.start_tangent_angle()
    end_angle = arc.end_tangent_angle()
    p1 = arc.p1 + geom.P.from_polar(offset, start_angle)
    p2 = arc.p2 + geom.P.from_polar(offset, end_angle)
    radius = math.hypot(offset, arc.radius)
    offset_arc = geom.Arc(p1, p2, radius, arc.angle, arc.center)
    offset_arc.inline_start_angle = start_angle
    offset_arc.inline_end_angle = end_angle
    return offset_arc


def fix_G1_path(path, tolerance, line_flatness):
    """
    """
    new_path = []
    if len(path) < 2:
        return path
    seg1 = path[0]
    cp1 = seg1.p1
    for seg2 in path[1:]:
        if getattr(seg1, 'g1', False):
            arcs, cp1 = smoothing_arcs(seg1, seg2, cp1,
                                       tolerance=tolerance, max_depth=1,
                                       line_flatness=line_flatness)
            new_path.extend(arcs)
        else:
            cp1 = seg2.p1
            new_path.append(seg1)
        seg1 = seg2
    # Process last segment...
    if getattr(seg1, 'g1', False):
        arcs, cp1 = smoothing_arcs(seg1, None, cp1,
                                   tolerance=tolerance, max_depth=1,
                                   line_flatness=line_flatness)
        new_path.extend(arcs)
    else:
        new_path.append(seg1)
    return new_path


def smoothing_arcs(seg1, seg2, cp1=None,
                   tolerance=0.0001, line_flatness=0.0001,
                   max_depth=1, match_arcs=True):
    """Create circular smoothing biarcs between two segments
    that are not currently G1 continuous.

    Args:
        seg1: First path segment containing first and second points.
            Can be a geom.Line or geom.Arc.
        seg2: Second path segment containing second and third points.
            Can be a geom.Line or geom.Arc.
        cp1: Control point computed from previous invocation.
        tolerance: Biarc matching tolerance.
        line_flatness: Curve to line tolerance.
        max_depth: Max Bezier subdivision recursion depth.
        match_arcs: Attempt to more closely match existing arc segments.
            Default is True.

    Returns:
        A tuple containing a list of biarc segments and the control point
        for the next curve.
    """
    curve, cp1 = geom.bezier.smoothing_curve(seg1, seg2, cp1, match_arcs)
#     geom.debug.draw_bezier(curve, color='#00ff44') #DEBUG
    biarc_segs = curve.biarc_approximation(tolerance=tolerance,
                                           max_depth=max_depth,
                                           line_flatness=line_flatness)
    if not biarc_segs:
        return ((seg1,), seg1.p2)
    # Compute total arc length of biarc approximation
    biarc_length = 0
    for seg in biarc_segs:
        biarc_length += seg.length()
    # Fix inline rotation hints for each new arc segment.
    a_start = util.seg_start_angle(seg1)
    a_end = a_start
    sweep = geom.normalize_angle(util.seg_end_angle(seg1) - a_start, center=0.0)
    sweep_scale = sweep / biarc_length
    for arc in biarc_segs:
        a_end = a_start + (arc.length() * sweep_scale)
        arc.inline_start_angle = a_start
        arc.inline_end_angle = a_end
        a_start = a_end
    return (biarc_segs, cp1)
