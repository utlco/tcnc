#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
Debug output support for geometry package.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *


# svg.SVGContext for drawing debug output. Default is None.
_SVG_CONTEXT = None

def svg_context():
    """The SVG context used for debug output."""
    return _SVG_CONTEXT

def set_svg_context(svg_context):
    """Initialize this module with an SVGContext that can be used
    for debug output by draw...() methods."""
    global _SVG_CONTEXT
    _SVG_CONTEXT = svg_context

def draw_point(point, radius=3, color='#000000', parent=None):
    """Draw a dot. Useful for debugging and testing."""
    svg = svg_context()
    if svg is not None:
        svg.create_circle(point, svg.unit2uu(radius),
                          style='fill:%s;stroke:none' % color,
                          parent=parent)


def draw_line(line, color='#c00000', width='1px', verbose=False, parent=None):
    """Draw an SVG line segment for debugging/testing"""
    svg = svg_context()
    if svg is not None:
        style = ('fill:none;stroke:%s;stroke-width:%f;stroke-opacity:1' %
                 (color, svg.unit2uu(width)))
        svg.create_line(line[0], line[1], style, parent=parent)
        if verbose:
            draw_point(line[0], color=color)
            draw_point(line[1], color=color)

def draw_poly(vertices, color='#c00000', width='1px', verbose=False,
              parent=None, close_poly=True):
    """Draw an SVG polygon.
    """
    svg = svg_context()
    if svg is not None:
        style = ('fill:none;stroke:%s;stroke-width:%f;stroke-opacity:1' %
                 (color, svg.unit2uu(width)))
        svg.create_polygon(vertices, close_polygon=close_poly,
                           style=style, parent=parent)
        if verbose:
            for p in vertices:
                draw_point(p, color=color)

def draw_arc(arc, color='#cccc99', width='1px', verbose=False, parent=None):
    """Draw an SVG arc for debugging/testing"""
    svg = svg_context()
    if svg is not None:
        style = ('fill:none;stroke:%s;stroke-width:%f;stroke-opacity:1' %
                 (color, svg.unit2uu(width)))
        attrs = {'d': arc.to_svg_path(), 'style': style}
        svg.create_path(attrs, parent=parent)
        if verbose:
            # Draw the center-arc wedge
            draw_point(arc.center, color=color, radius='2px')
            draw_line((arc.center, arc.p1), color=color, parent=parent)
            draw_line((arc.center, arc.p2), color=color, parent=parent)
            draw_point(arc.p1, color='#cc99cc', radius='2px')
            draw_point(arc.p2, color='#99cccc', radius='2px')


def draw_circle(center, radius, color='#cccc99', width='1px',
                verbose=False, parent=None):
    """Draw an SVG circle."""
    svg = svg_context()
    if svg is not None:
        style = ('fill:none;stroke:%s;stroke-width:%s;'
                 'stroke-opacity:1') % (color, svg.unit2uu(width))
        svg.create_circle(center, radius,
                          style=style, parent=parent)
        if verbose:
            draw_point(center, color=color, parent=parent)


def draw_ellipse(ellipse, color='#cccc99', width='1px',
                verbose=False, parent=None):
    """Draw an SVG arc for debugging/testing"""
    svg = svg_context()
    if svg is not None:
        style = ('fill:none;stroke:%s;stroke-width:%s;'
                 'stroke-opacity:1') % (color, svg.unit2uu(width))
        svg.create_ellipse(ellipse.center, ellipse.rx, ellipse.ry,
                          angle=ellipse.phi, style=style, parent=parent)
        if verbose:
            draw_point(ellipse.center, color=color, parent=parent)


def draw_bezier(curve, color='#cccc99', verbose=False, parent=None):
    """Draw an SVG version of this curve for debugging/testing.
    Include control points, inflection points, and tangent lines.
    """
    svg = svg_context()
    if svg is not None:
        style = ('fill:none;stroke:%s;stroke-width:%f;stroke-opacity:1' %
                 (color, svg_context().unit2uu(1)))
        attrs = {'d': curve.to_svg_path(), 'style': style}
        svg.create_path(attrs, parent=parent)
        if verbose:
            # Draw control points and tangents
            draw_point(curve.c1, color='#0000c0', parent=parent)
            draw_point(curve.c2, color='#0000c0', parent=parent)
            draw_line((curve.p1, curve.c1), parent=parent)
            draw_line((curve.p2, curve.c2), parent=parent)
            # Draw inflection points if any
            t1, t2 = curve.find_inflections()
            if t1 > 0.0:
                # ip1 = curve.controlpoints_at(t1)[2]
                ip1 = curve.point_at(t1)
                draw_point(ip1, color='#c00000', parent=parent)
            if t2 > 0.0:
                # ip2 = curve.controlpoints_at(t2)[2]
                ip2 = curve.point_at(t2)
                draw_point(ip2, color='#c00000', parent=parent)
            # Draw midpoint
            mp = curve.point_at(0.5)
            draw_point(mp, color='#00ff00', parent=parent)


