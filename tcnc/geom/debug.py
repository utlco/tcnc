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

from . import (point, line, arc, ellipse, bezier)


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

def draw_obj(obj, color='#c00000', parent=None):
    """Draw a geom object."""
    if isinstance(obj, point.P):
        draw_point(obj, color=color, parent=parent)
    elif isinstance(obj, line.Line):
        draw_line(obj, color=color, parent=parent)
    elif isinstance(obj, arc.Arc):
        draw_arc(obj, color=color, parent=parent)
    elif isinstance(obj, ellipse.Ellipse):
        draw_ellipse(obj, color=color, parent=parent)
    elif isinstance(obj, bezier.CubicBezier):
        draw_bezier(obj, color=color, parent=parent)

def draw_point(point, color='#000000', radius=3, parent=None):
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
        svg.create_line(line.p1, line.p2, style, parent=parent)
        if verbose:
            draw_point(line.p1, color=color)
            draw_point(line.p2, color=color)


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
            seg1 = line.Line(arc.center, arc.p1)
            seg2 = line.Line(arc.center, arc.p2)
            draw_point(arc.center, color=color, radius='2px')
            draw_line(seg1, color=color, parent=parent)
            draw_line(seg2, color=color, parent=parent)
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


def draw_bezier(bezier, color='#cccc99', verbose=False, parent=None):
    """Draw an SVG version of this curve for debugging/testing.
    Include control points, inflection points, and tangent lines.
    """
    svg = svg_context()
    if svg is not None:
        style = ('fill:none;stroke:%s;stroke-width:%f;stroke-opacity:1' %
                 (color, svg_context().unit2uu(1)))
        attrs = {'d': bezier.to_svg_path(), 'style': style}
        svg.create_path(attrs, parent=parent)
        if verbose:
            # Draw control points and tangents
            draw_point(bezier.c1, color='#0000c0', parent=parent)
            draw_point(bezier.c2, color='#0000c0', parent=parent)
            tseg1 = line.Line(bezier.p1, bezier.c1)
            draw_line(tseg1, parent=parent)
            tseg2 = line.Line(bezier.p2, bezier.c2)
            draw_line(tseg2, parent=parent)
            # Draw inflection points if any
            t1, t2 = bezier.find_inflections()
            if t1 > 0.0:
                #ip1 = bezier.controlpoints_at(t1)[2]
                ip1 = bezier.point_at(t1)
                draw_point(ip1, color='#c00000', parent=parent)
            if t2 > 0.0:
                #ip2 = bezier.controlpoints_at(t2)[2]
                ip2 = bezier.point_at(t2)
                draw_point(ip2, color='#c00000', parent=parent)
            # Draw midpoint
            mp = bezier.point_at(0.5)
            draw_point(mp, color='#00ff00', parent=parent)


def plot_path(path, color, layer):
    """Debug output for paths."""
#     prev_seg = None
    segnum = 1
    for seg in path:
#         logger.debug('\nSegment %d: %s' % (segnum, str(seg)))
#         if prev_seg is not None and prev_seg.p2 != seg.p1:
#             logger.debug('path not continuous: p1=%s, p2=%s' % (str(prev_seg.p2), str(seg.p1)))
#             prev_seg.p2.svg_plot(color='#0000ff')
#             seg.p1.svg_plot(color='#0000ff')
#         for name in inline_hint_attrs(seg):
#             logger.debug('%s=%s' % str(getattr(seg, name)))
        draw_obj(seg, color=color, parent=layer)
#         prev_seg = seg
        segnum += 1


