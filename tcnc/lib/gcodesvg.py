#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
SVG Preview plotter for Gcode generator.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import math
import logging

from lib import geom
from lib import gcode


class SVGPreviewPlotter(gcode.PreviewPlotter):
    """Provides a graphical preview of the G-code output.

    Outputs SVG.

    Draws a line along the tool path as well as tool marks that
    show the current rotation of a tangential tool that rotates
    about the Z axis.
    """
    _styles = {
        'toolpath_end_marker':
            'fill-rule:evenodd;fill:$feedline_stroke;'
            'stroke:none;marker-start:none',
        'movepath_end_marker':
            'fill-rule:evenodd;fill:$moveline_stroke;'
            'stroke:none;marker-start:none',
        'feedline':
            'fill:none;stroke:$feedline_stroke;'
            'stroke-width:$feedline_stroke_width'
            ';stroke-opacity:1.0;marker-end:url(#PreviewLineEnd0)',
        'feedarc':
            'fill:none;stroke:$feedline_stroke;'
            'stroke-width:$feedline_stroke_width'
            ';stroke-linecap:butt;stroke-linejoin:miter;stroke-miterlimit:4'
            ';stroke-opacity:1.0;marker-end:url(#PreviewLineEnd0)',
        'moveline':
            'fill:none;stroke:$moveline_stroke;'
            'stroke-width:$moveline_stroke_width'
            ';marker-end:url(#PreviewLineEnd2)',
        'toolmark':
            'fill:none;stroke:$toolmark_stroke;'
            'stroke-width:$toolmark_stroke_width;'
            'stroke-opacity:0.75',
        'tooloffset':
            'fill:none;stroke:$tooloffset_stroke;'
            'stroke-width:$tooloffset_stroke_width;'
            'stroke-opacity:0.75',
    }
    # Default style template mapping
    _style_defaults = {
            'feedline_stroke':  '#ff3030',
            'moveline_stroke':  '#10cc10',
            'toolmark_stroke':  '#ff6060',
            'tooloffset_stroke':  '#cccccc',
    }
    _style_scale_defaults = {
        'small': {
            'feedline_stroke_width': '1px',
            'moveline_stroke_width': '1px',
            'toolmark_stroke_width': '2px',
            'tooloffset_stroke_width': '1px',
            'end_marker_scale': '0.38'},
        'medium': {
            'feedline_stroke_width': '2pt',
            'moveline_stroke_width': '2pt',
            'toolmark_stroke_width': '3pt',
            'tooloffset_stroke_width': '2px',
            'end_marker_scale': '0.38'},
        'large': {
            'feedline_stroke_width': '3.5pt',
            'moveline_stroke_width': '3.5pt',
            'toolmark_stroke_width': '.2in',
            'tooloffset_stroke_width': '2px',
            'end_marker_scale': '0.38'},
    }
    _line_end_markers = (
        ('PreviewLineEnd0', 'M 5.77,0.0 L -2.88,5.0 L -2.88,-5.0 L 5.77,0.0 z',
         'toolpath_end_marker', 'scale(%s) translate(-4.5,0)'),
        ('PreviewLineEnd1', 'M 5.77,0.0 L -2.88,5.0 L -2.88,-5.0 L 5.77,0.0 z',
         'toolpath_end_marker', 'scale(-%s) translate(-4.5,0)'),
        ('PreviewLineEnd2', 'M 5.77,0.0 L -2.88,5.0 L -2.88,-5.0 L 5.77,0.0 z',
         'movepath_end_marker', 'scale(%s) translate(-4.5,0)'),
    )

    PATH_LAYER_NAME = 'tcnc-path-preview'
    TOOL_LAYER_NAME = 'tcnc-tool-preview'

    _DEFAULT_TOOLMARK_INTERVAL_LINE = '10px'
    _DEFAULT_TOOLMARK_INTERVAL_ANGLE = math.pi / 10

    def __init__(self, svg_context, tool_offset=0.0, tool_width=0.0,
                 toolmark_line_interval=None,
                 toolmark_rotation_interval=None, style_scale="medium",
                 *args, **kwargs):
        """
        Args:
            svg_context: An instance of svg.SVGContext to render output.
            gc: An instance of GCode that will call back to this plotter.
            tool_offset: Tangential tool offset. Optional, default is 0.
            tool_width: Tangential tool width. Optional, default is 0.
            toolmark_line_interval: Spacing of tool marks along straight lines.
                Specified in SVG user units.
            toolmark_rotation_interval: Spacing of tool marks along arcs.
                Specified in radians.
            style_scale: Scale of preview lines and glyphs. String.
                Can be 'small', 'medium', or 'large'. Default is 'medium'.
        """
        super(SVGPreviewPlotter, self).__init__(*args, **kwargs)

        self.svg = svg_context
        # Tangential tool offset.
        self.tool_offset = tool_offset
        # Tangential tool width.
        self.tool_width = tool_width
        # Tool mark interval along lines and arcs. In user units.
        if toolmark_line_interval is None:
            interval = self.svg.unit2uu(self._DEFAULT_TOOLMARK_INTERVAL_LINE)
            self.toolmark_line_interval = interval
        else:
            self.toolmark_line_interval = toolmark_line_interval
        # Tool mark interval for in place rotation. In radians.
        if toolmark_rotation_interval is None:
            self.toolmark_rotation_interval = self._DEFAULT_TOOLMARK_INTERVAL_ANGLE
        else:
            self.toolmark_rotation_interval = toolmark_rotation_interval

        # Current XYZA location
        self._current_xy = geom.P(0.0, 0.0)
        self._current_z = 0.0
        self._current_a = 0.0

        # Initialize CSS styles used for rendering
        style_scale_values = self._style_scale_defaults[style_scale]
        self._style_defaults.update(style_scale_values)
        self._styles.update(self.svg.styles_from_templates(self._styles,
                                                           self._style_defaults))

        # Create layers that will contain the G code preview
        self.path_layer = self.svg.create_layer(self.PATH_LAYER_NAME,
                                                flipy=True)
        if self.tool_offset == 0.0 and self.tool_width == 0.0:
            self.tool_layer = None
        else:
            self.tool_layer = self.svg.create_layer(self.TOOL_LAYER_NAME,
                                                    flipy=True)
        svg_context.set_default_parent(self.path_layer)

        # Create Inkscape line end marker glyphs
        for marker in self._line_end_markers:
            transform = marker[3] % style_scale_values['end_marker_scale']
            self.svg.create_simple_marker(marker[0], marker[1],
                                          self._styles[marker[2]],
                                          transform, replace=True)

    def plot_move(self, endp):
        """Plot G00 - rapid move from current position to :endp:(x,y,z,a)."""
        self.svg.create_line(self._current_xy, endp, self._styles['moveline'])
        self._update_location(endp)

    def plot_feed(self, endp):
        """Plot G01 - linear feed from current position to :endp:(x,y,z,a)."""
        if self._current_xy.distance(endp) > geom.const.EPSILON:
            self.svg.create_line(self._current_xy, endp,
                                 self._styles['feedline'])
        self._draw_tool_marks(geom.Line(self._current_xy, endp),
                              start_angle=self._current_a, end_angle=endp[3])
        self._update_location(endp)

    def plot_arc(self, center, endp, clockwise):
        """Plot G02/G03 - arc feed from current position to :endp:(x,y,z,a)."""
        center = geom.P(center)
        radius = center.distance(self._current_xy)
#         assert(self.gcgen.float_eq(center.distance(endp), radius))
        if not self.gcgen.float_eq(center.distance(endp), radius):
            logging.getLogger(__name__).debug(
                'Degenrate arc: d1=%f, d2=%f', center.distance(endp), radius)
        sweep_flag = 0 if clockwise else 1
#         style = self._styles['feedarc' + str(sweep_flag)]
        style = self._styles['feedarc']
        self.svg.create_circular_arc(self._current_xy, endp, radius,
                                     sweep_flag, style)
        angle = center.angle2(self._current_xy, endp)
        arc = geom.Arc(self._current_xy, endp, radius, angle, center)
        self._draw_tool_marks(arc, self._current_a, endp[3])
        self._update_location(endp)

    def _draw_tool_marks(self, segment, start_angle, end_angle):
        """Draw marks showing the angle and travel of the tangential tool."""
        if self.tool_layer is None:
            return
        seglen = segment.length()
        rotation = end_angle - start_angle
        if seglen > 0:
            num_markers = int(seglen / self.toolmark_line_interval)
            num_markers = max(1, num_markers)
        else:
            num_markers = int(abs(rotation) / self.toolmark_rotation_interval)
            num_markers = max(1, num_markers)
        angle_incr = rotation / num_markers
        point_incr = 1.0 / num_markers
#         logger.debug('len=%.4f, n=%d, aincr=%.4f, pincr=%.4f' % (seglen, num_markers, angle_incr, point_incr))
        angle = start_angle
        u = 0
        while u <= 1.0:
            self._draw_tool_mark(segment, u, angle)
            angle += angle_incr
            u += point_incr
#         self._draw_tool_mark(segment, 1.0, end_angle)

    def _draw_tool_mark(self, segment, u, angle):
        p = segment.point_at(u)
        if not self.gcgen.float_eq(self.tool_offset, 0.0):
            px = p + geom.P.from_polar(self.tool_offset, angle - math.pi)
            self.svg.create_line(p, px, self._styles['tooloffset'],
                                 parent=self.tool_layer)
        else:
            px = p
        if self.tool_width > self.gcgen.tolerance:
            r = self.tool_width / 2
            p1 = px + geom.P.from_polar(r, angle + math.pi/2)
            p2 = px + geom.P.from_polar(r, angle - math.pi/2)
            self.svg.create_line(p1, p2, self._styles['toolmark'],
                                 parent=self.tool_layer)

    def _update_location(self, endp):
        self._current_xy = geom.P(endp[0], endp[1])
        self._current_z = endp[2]
        self._current_a = endp[3]

