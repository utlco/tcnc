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

import math
# import logging

from lib import geom

from . import const
from . import util
from .line import Line
from .arc import Arc
from .point import P


def fillet_path(path, radius, fillet_close=True):
    """Attempt to insert a circular arc of the specified radius
    to connect adjacent path segments.

    Args:
        path: A list of Line or Arc segments.
        radius: The radius of the fillet arc.
        fillet_close: If True and the path is closed then
            add a terminating fillet. Default is False.

    Returns:
        A new path with fillet arcs. If no fillets are created then
        the original path will be returned.
    """
    if radius < const.EPSILON or len(path) < 2:
        return path
    new_path = []
    seg1 = path[0]
    for seg2 in path[1:]:
        new_segs = insert_fillet(seg1, seg2, radius)
        if new_segs:
            new_path.extend(new_segs[:-1])
            seg2 = new_segs[-1]
        else:
            new_path.append(seg1)
        seg1 = seg2
    new_path.append(seg1)
    # Close the path with a fillet
    if fillet_close and len(path) > 2 and path[0].p1 == path[-1].p2:
        new_segs = insert_fillet(new_path[-1], new_path[0], radius)
        if new_segs:
            new_path[-1] = new_segs[0]
            new_path.append(new_segs[1])
            new_path[0] = new_segs[2]
    # Discard the path copy if no fillets were created...
    return new_path if len(new_path) > len(path) else path


def fillet_polygon(poly, radius, fillet_close=True):
    """Attempt to insert a circular arc of the specified radius
    connecting adjacent polygon segments.

    Args:
        poly: A list of polygon vertices.
        radius: The radius of the fillet arc.
        fillet_close: If True and the path is closed then
            add a terminating fillet. Default is False.

    Returns:
        A new path with fillet arcs as a list of Line and Arc segments.
        If no fillets are created then the original path will be returned.
    """
    if len(poly) < 2:
        return ()
    seg1 = Line(poly[0], poly[1])
    if len(poly) == 2:
        return (seg1,)
    path = []
    for p in poly[2:]:
        seg2 = Line(seg1.p2, p)
        new_segs = insert_fillet(seg1, seg2, radius)
        if new_segs:
            path.append(new_segs[0])
            path.append(new_segs[1])
            seg1 = new_segs[2]
        else:
            path.append(seg1)
            seg1 = seg2
    path.append(seg1)
    if fillet_close and len(path) > 2 and path[0].p1 == path[-1].p2:
        new_segs = insert_fillet(path[-1], path[0], radius)
        if new_segs:
            path[-1] = new_segs[0]
            path.append(new_segs[1])
            path[0] = new_segs[2]
    return path


def insert_fillet(seg1, seg2, radius):
    """Try to create a fillet between two segments.
    Any GCode rendering hints attached to the segments will
    be preserved.

    Args:
        seg1: First segment, an Arc or a Line.
        seg2: Second segment, an Arc or a Line.
        radius: Fillet radius.

    Returns:
        A tuple containing the adjusted segments and fillet arc:
        (seg1, fillet_arc, seg2)
        Returns an empty tuple if the segments cannot be connected
        with a fillet arc (either they are too small
        or somehow degenerate.)
    """
    farc = create_fillet_arc(seg1, seg2, radius)
    if farc is None:
        return ()
    return connect_fillet(seg1, farc, seg2)


def connect_fillet(seg1, farc, seg2):
    """Connect two segments with a fillet arc.
    This will adjust the lengths of the segments to
    accommodate the fillet."""
    if isinstance(seg1, Line):
        new_seg1 = Line(seg1.p1, farc.p1)
        if isinstance(seg2, Line):
            # Connect Line->Fillet->Line
            new_seg2 = Line(farc.p2, seg2.p2)
        else:
            # Connect Line->Fillet->Arc
            new_angle = seg2.angle - seg2.center.angle2(seg2.p1, farc.p2)
            new_seg2 = Arc(farc.p2, seg2.p2, seg2.radius, new_angle,
                                seg2.center)
    else:
        new_angle = seg1.angle - seg1.center.angle2(farc.p1, seg1.p2)
        new_seg1 = Arc(seg1.p1, farc.p1, seg1.radius, new_angle,
                            seg1.center)
        if isinstance(seg2, Line):
            # Connect Arc->Fillet->Line
            new_seg2 = Line(farc.p2, seg2.p2)
        else:
            # Connect Arc->Fillet->Arc
            new_angle = seg2.angle - seg2.center.angle2(seg2.p1, farc.p2)
            new_seg2 = Arc(farc.p2, seg2.p2, seg2.radius, new_angle,
                                seg2.center)
    return (new_seg1, farc, new_seg2)


def create_fillet_arc(seg1, seg2, radius):
    """Try to create a fillet between two segments.

    Args:
        seg1: First segment, an Arc or a Line.
        seg2: Second segment, an Arc or a Line.
        radius: Fillet radius.

    Returns:
        A fillet arc or None if the segments cannot be connected
        with a fillet arc (either they are too small, already G1
        continuous, or are somehow degenerate.)
    """
    farc = None
    if isinstance(seg1, Line):
        if isinstance(seg2, Line):
            farc = fillet_line_line(seg1, seg2, radius)
        elif isinstance(seg2, Arc):
            farc = fillet_line_arc(seg1, seg2, radius)
    elif isinstance(seg1, Arc):
        if isinstance(seg2, Line):
            farc = fillet_line_arc(seg2, seg1, radius)
        elif isinstance(seg2, Arc):
            farc = fillet_arc_arc(seg1, seg2, radius)
    return farc


def fillet_line_line(line1, line2, fillet_radius):
    """Create a fillet arc between two line segments.

    Args:
        line1: A Line.
        line2: A Line connected to line1.
        fillet_radius: The radius of the fillet.

    Returns:
        An Arc, or None if the fillet radius is too big to fit or
        if the two segments are not connected.
    """
    fillet_arc = None # default return value
    lineside = line1.which_side(line2.p2)
    offset = fillet_radius * lineside
    offset_line1 = line1.offset(offset)
    offset_line2 = line2.offset(offset)
    fillet_center = offset_line1.intersection(offset_line2)
    if fillet_center is not None:
        fp1 = line1.normal_projection_point(fillet_center, segment=True)
        fp2 = line2.normal_projection_point(fillet_center, segment=True)
        # Test for fillet fit
        if (fp1 is not None and fp2 is not None and fp1 != fp2
                and geom.float_eq(fp1.distance(fillet_center), fillet_radius)
                and geom.float_eq(fp2.distance(fillet_center), fillet_radius)):
            fillet_arc = Arc.from_two_points_and_center(fp1, fp2,
                                                       fillet_center)
    return fillet_arc


def fillet_arc_arc(arc1, arc2, fillet_radius):
    """Create a fillet arc between two connected arcs.

    Args:
        arc1: First arc.
        arc2: Second arc.
        fillet_radius: The radius of the fillet.

    Returns:
        An Arc,
        or None if the fillet radius is too big to fit or
        if the two segments are not connected.
    """
    fillet_arc = None # default return value
    arc2_side = arc1.which_side_angle(arc2.start_tangent_angle())
    cw1 = 1 if arc1.is_clockwise() else -1
    cw2 = 1 if arc2.is_clockwise() else -1
    oarc1 = arc1.offset(fillet_radius * arc2_side * cw1)
    oarc2 = arc2.offset(fillet_radius * arc2_side * cw2)
    # The intersection of the two offset arcs is the fillet arc center.
    ix = oarc1.intersect_arc(oarc2, on_arc=True)
    if ix:
        fillet_center = ix[0]
        # Find points normal from fillet center to arc segments
        fline1 = Line(fillet_center, arc1.center)
        fline2 = Line(fillet_center, arc2.center)
        ix1 = arc1.intersect_line(fline1, on_arc=True)
        ix2 = arc2.intersect_line(fline2, on_arc=True)
        if ix1 and ix2:
            fillet_arc = Arc.from_two_points_and_center(ix1[0], ix2[0],
                                                             fillet_center)
    return fillet_arc


def fillet_line_arc(line, arc, fillet_radius):
    """Create a fillet arc between a line segment and a connected arc.
    The fillet arc end point order will match the line-arc order.

    Args:
        line: A Line.
        arc: An Arc.
        fillet_radius: The radius of the fillet.

    Returns:
        An Arc,
        or None if the fillet radius is too big to fit or
        if the two segments are not connected.
    """
    # TODO: Maybe replace this novel approach with the more usual
    # offset intersection method..
    fillet_arc = None # default return value

    # If the direction is arc->line then reverse both
    # to make things simpler.
    is_reversed = False
    if geom.float_eq(arc.p2, line.p1):
        # The two segments are connected but in reverse order.
        line = line.reversed()
        arc = arc.reversed()
        is_reversed = True

    arc_side = line.which_side_angle(arc.start_tangent_angle())
    if ((arc_side > 0 and arc.is_clockwise()) or
        (arc_side < 0 and not arc.is_clockwise())):
        h = arc.radius + fillet_radius
        alpha1 = line.angle() + math.pi
    else:
        h = arc.radius - fillet_radius
        alpha1 = line.angle()
    line3 = line.offset(fillet_radius * arc_side)
    p5 = line3.normal_projection_point(arc.center)
    b = p5.distance(arc.center)
    a2 = h*h - b*b
    if a2 < 0:
        return
    a = math.sqrt(a2)
    line4 = Line.from_polar(p5, a, alpha1)
    fillet_center = line4.p2
    alpha2 = abs(arc.center.angle2(arc.p1, fillet_center))
    fp1 = line.normal_projection_point(fillet_center, segment=True)
    fp2 = arc.point_at_angle(alpha2, segment=True)
    if (fp1 is not None and fp2 is not None and fp1 != fp2 and
        geom.float_eq(fillet_center.distance(fp1),
                      fillet_center.distance(fp2))):
        if is_reversed:
            fillet_arc = Arc.from_two_points_and_center(fp2, fp1,
                                                             fillet_center)
        else:
            fillet_arc = Arc.from_two_points_and_center(fp1, fp2,
                                                             fillet_center)
    return fillet_arc
