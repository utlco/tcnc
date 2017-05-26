#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
Methods for converting SVG shape elements to geometry objects.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import math
import logging

import geom

from geom import transform2d
from geom import bezier

from . import svg


def svg_to_geometry(svg_elements, parent_transform=None):
    """Convert the SVG shape elements to
    Line, Arc, and/or CubicBezier segments,
    and apply node/parent transforms.
    The coordinates of the segments will be absolute with
    respect to the parent container.

    Args:
        svg_elements: An iterable collection of 2-tuples consisting of
            SVG Element node and transform matrix.
        parent_transform: An optional parent transform to apply to all
            nodes. Default is None.

    Returns:
        A list of paths, where a path is a list of one or more
        segments made of Line, Arc, or CubicBezier objects.
    """
    path_list = []
    for element, element_transform in svg_elements:
        transformed_paths = svg_element_to_geometry(element,
                                                   element_transform,
                                                   parent_transform)
        if transformed_paths:
            path_list.extend(transformed_paths)
    return path_list


def svg_element_to_geometry(element, element_transform=None,
                            parent_transform=None):
    """Convert the SVG shape element to a list of one or more
    Line, Arc, and/or CubicBezier segments,
    and apply node/parent transforms.
    The coordinates of the segments will be absolute with
    respect to the parent container.

    Args:
        element: An SVG Element shape node.
        element_transform: An optional transform to apply to the element.
            Default is None.
        parent_transform: An optional parent transform to apply to the element.
            Default is None.

    Returns:
        A list of zero or more paths.
        A path being a list of zero or more Line, Arc, EllipticalArc,
        or CubicBezier objects.
    """
    # Convert the element to a list of subpaths
    subpath_list = []
    tag = svg.strip_ns(element.tag) # tag stripped of namespace part
    if tag == 'path':
        d = element.get('d')
        if d is not None and d:
            subpath_list = parse_path_geom(d, ellipse_to_bezier=True)
    else:
        subpath = []
        if tag == 'line':
            subpath = convert_line(element)
        elif tag == 'ellipse':
            ellipse = convert_ellipse(element)
            subpath = bezier.bezier_ellipse(ellipse)
        elif tag == 'rect':
            subpath = convert_rect(element)
        elif tag == 'circle':
            subpath = convert_circle(element)
        elif tag == 'polyline':
            subpath = convert_polyline(element)
        elif tag == 'polygon':
            subpath = convert_polygon(element)
        if subpath:
            subpath_list = [subpath, ]

    if subpath_list:
        # Create a transform matrix that is composed of the
        # parent transform and the element transform
        # so that control points are in absolute coordinates.
        if parent_transform is not None:
            element_transform = transform2d.compose_transform(
                                                    parent_transform,
                                                    element_transform)
        if element_transform is not None:
            x_subpath_list = []
            for subpath in subpath_list:
                x_subpath = []
                for segment in subpath:
                    # Skip zero-length segments.
                    if not segment.p1 == segment.p2:
                        segment = segment.transform(element_transform)
                        x_subpath.append(segment)
                x_subpath_list.append(x_subpath)
            return x_subpath_list
    return subpath_list


def parse_path_geom(path_data, ellipse_to_bezier=False):
    """
    Parse SVG path data and convert to geometry objects.

    Args:
        path_data: The `d` attribute value of an SVG path element.
        ellipse_to_bezier: Convert elliptical arcs to bezier curves
            if True. Default is False.

    Returns:
        A list of zero or more subpaths.
        A subpath being a list of zero or more Line, Arc, EllipticalArc,
        or CubicBezier objects.
    """
    subpath = []
    subpath_list = []
    p1 = (0.0, 0.0)
    for cmd, params in svg.parse_path(path_data):
        p2 = (params[-2], params[-1])
        if cmd == 'M':
            if subpath:
                subpath_list.append(subpath)
                subpath = []
        elif cmd == 'L':
            subpath.append(geom.Line(p1, p2))
        elif cmd == 'A':
            rx = params[0]
            ry = params[1]
            phi = params[2]
            large_arc = params[3]
            sweep_flag = params[4]
            elliptical_arc = geom.ellipse.EllipticalArc.from_endpoints(
                p1, p2, rx, ry, large_arc, sweep_flag, phi)
            if elliptical_arc is None:
                # Parameters must be degenerate...
                # Try just making a line
                logger = logging.getLogger(__name__)
                logger.debug('Degenerate arc...')
                subpath.append(geom.Line(p1, p2))
            elif geom.float_eq(rx, ry):
                # If it's a circular arc then create one using
                # the previously computed ellipse parameters.
                segment = geom.Arc(p1, p2, rx, elliptical_arc.sweep_angle,
                                   elliptical_arc.center)
                subpath.append(segment)
            elif ellipse_to_bezier:
                # Convert the elliptical arc to cubic Beziers
                subpath.extend(bezier.bezier_ellipse(elliptical_arc))
            else:
                subpath.append(elliptical_arc)
        elif cmd == 'C':
            c1 = (params[0], params[1])
            c2 = (params[2], params[3])
            subpath.append(bezier.CubicBezier(p1, c1, c2, p2))
        elif cmd == 'Q':
            c1 = (params[0], params[1])
            subpath.append(bezier.CubicBezier.from_quadratic(p1, c1, p2))
        p1 = p2
    if subpath:
        subpath_list.append(subpath)
    return subpath_list


def convert_rect(element):
    """Convert an SVG rect shape element to four geom.Line segments.

    Args:
        element: An SVG 'rect' element of the form
            <rect x='X' y='Y' width='W' height='H'/>

    Returns:
        A clockwise wound polygon as a list of geom.Line segments.
    """
    # Convert to a clockwise wound polygon
    x1 = float(element.get('x', 0))
    y1 = float(element.get('y', 0))
    x2 = x1 + float(element.get('width', 0))
    y2 = y1 + float(element.get('height', 0))
    p1 = (x1, y1)
    p2 = (x1, y2)
    p3 = (x2, y2)
    p4 = (x2, y1)
    return [geom.Line(p1, p2), geom.Line(p2, p3), geom.Line(p3, p4),
            geom.Line(p4, p1)]


def convert_line(element):
    """Convert an SVG line shape element to a geom.Line.

    Args:
        element: An SVG 'line' element of the form:
           <line x1='X1' y1='Y1' x2='X2' y2='Y2/>

    Returns:
       A line segment: geom.Line((x1, y1), (x2, y2))
    """
    x1 = float(element.get('x1', 0))
    y1 = float(element.get('y1', 0))
    x2 = float(element.get('x2', 0))
    y2 = float(element.get('y2', 0))
    return geom.Line((x1, y1), (x2, y2))


def convert_circle(element):
    """Convert an SVG circle shape element to four circular arc segments.

    Args:
        element: An SVG 'circle' element of the form:
           <circle r='RX' cx='X' cy='Y'/>
    Returns:
       A counter-clockwise wound list of four circular geom.Arc segments.
    """
    # Convert to four arcs. CCW winding.
    r = abs(float(element.get('r', 0)))
    cx = float(element.get('cx', 0))
    cy = float(element.get('cy', 0))
    center = (cx, cy)
    p1 = (cx + r, cy)
    p2 = (cx, cy + r)
    p3 = (cx - r, cy)
    p4 = (cx, cy - r)
    a1 = geom.Arc(p1, p2, r, math.pi / 2, center)
    a2 = geom.Arc(p2, p3, r, math.pi / 2, center)
    a3 = geom.Arc(p3, p4, r, math.pi / 2, center)
    a4 = geom.Arc(p4, p1, r, math.pi / 2, center)
    return [a1, a2, a3, a4]


def convert_ellipse(element):
    """Convert an SVG ellipse shape element to a geom.Ellipse.

    Args:
        element: An SVG 'ellipse' element of the form:
            <ellipse rx='RX' ry='RY' cx='X' cy='Y'/>

    Returns:
       A geom.Ellipse.
    """
    rx = float(element.get('rx', 0))
    ry = float(element.get('ry', 0))
    cx = float(element.get('cx', 0))
    cy = float(element.get('cy', 0))
    return geom.ellipse.Ellipse((cx, cy), rx, ry)


def convert_polyline(element):
    """Convert an SVG `polyline` shape element to a list of line segments.

    Args:
        element: An SVG 'polyline' element of the form:
            <polyline points='x1,y1 x2,y2 x3,y3 [...]'/>

    Returns:
       A list of geom.Line segments.
    """
    segments = []
    points = element.get('points', '').split()
    sx, sy = points[0].split(',')
    start_p = geom.P(float(sx), float(sy))
    prev_p = start_p
    for point in points[1:]:
        sx, sy = point.split(',')
        p = geom.P(float(sx), float(sy))
        segments.append(geom.Line(prev_p, p))
        prev_p = p
    return segments


def convert_polygon(element):
    """Convert an SVG `polygon` shape element to a list line segments.

    Args:
        element: An SVG 'polygon' element of the form:
            <polygon points='x1,y1 x2,y2 x3,y3 [...]'/>

    Returns:
       A list of geom.Line segments. The polygon will be closed.
    """
    segments = convert_polyline(element)
    # Close the polygon if not already so
    if len(segments) > 1 and segments[-1] != segments[0]:
        segments.append(geom.Line(segments[-1], segments[0]))
    return segments
