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

import geom

from . import gcode

logger = logging.getLogger(__name__)

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
        'toolmark_outline':
            'fill:$tm_outline_fill;stroke:$tm_outline_stroke;'
            'stroke-width:$tm_outline_stroke_width;'
            'stroke-opacity:0.75;'
            'fill-opacity:0.5;',
        'tooloffset':
            'fill:none;stroke:$tooloffset_stroke;'
            'stroke-width:$tooloffset_stroke_width;'
            'stroke-opacity:0.75',
        'subpath':
            'fill:none;stroke:$subpath_stroke;'
            'stroke-width:$subpath_stroke_width;',
    }
    # Default style template mapping
    _style_defaults = {
            'feedline_stroke': '#ff3030',
            'moveline_stroke': '#10cc10',
            'toolmark_stroke': '#ff6060',
            'tooloffset_stroke': '#3030ff',
            'tm_outline_stroke': 'none',
            'tm_outline_stroke_width': '1px',
            'tm_outline_fill': '#a0a0a0',
            'subpath_stroke': '#000000',
            'subpath_stroke_width': '1px',
    }
    _style_scale_defaults = {
        'small': {
            'feedline_stroke_width': '1px',
            'moveline_stroke_width': '1px',
            'toolmark_stroke_width': '1px',
            'tooloffset_stroke_width': '1px',
            'end_marker_scale': '0.38'},
        'medium': {
            'feedline_stroke_width': '1pt',
            'moveline_stroke_width': '1pt',
            'toolmark_stroke_width': '1pt',
            'tooloffset_stroke_width': '1pt',
            'end_marker_scale': '0.38'},
        'large': {
            'feedline_stroke_width': '2pt',
            'moveline_stroke_width': '2pt',
            'toolmark_stroke_width': '2pt',
            'tooloffset_stroke_width': '1.5pt',
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

    PATH_LAYER_NAME = 'tcnc preview: tool path'
    TOOL_LAYER_NAME = 'tcnc preview: tangent tool'
    SUBPATH_LAYER_NAME = 'subpaths (tcnc)'

    _DEFAULT_TOOLMARK_INTERVAL_LINE = '10px'
    _DEFAULT_TOOLMARK_INTERVAL_ANGLE = math.pi / 10

    def __init__(self, svg_context, tool_offset=0.0, tool_width=0.0,
                 toolmark_line_interval=None,
                 toolmark_rotation_interval=None, style_scale="small",
                 show_toolmarks=False, show_tm_outline=False,
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
            show_toolmarks: Show a preview of the tangent tool if True.
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

        self.show_toolmarks = show_toolmarks
        self.show_tm_outline = show_tm_outline

        # TODO: make this an option... (?)
        self.incr_layer_suffix = True

        # Experimental subpath options - these aren't usually exposed publicly...
        self.x_subpath_render = False
        self.x_subpath_layer_name = self.SUBPATH_LAYER_NAME
        self.x_subpath_offset = 0
        self.x_subpath_smoothness = .5
        self.x_subpath_layer = None

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
        self.tool_layer = None
        if (self.tool_offset > 0.0 and self.tool_width > 0.0
                and (self.show_toolmarks or self.show_tm_outline)):
            self.tool_layer = self.svg.create_layer(self.TOOL_LAYER_NAME,
                                            incr_suffix=self.incr_layer_suffix,
                                            flipy=True)

        self.path_layer = self.svg.create_layer(self.PATH_LAYER_NAME,
                                            incr_suffix=self.incr_layer_suffix,
                                            flipy=True)
        svg_context.set_default_parent(self.path_layer)

        # Create Inkscape line end marker glyphs
        for marker in self._line_end_markers:
            transform = marker[3] % style_scale_values['end_marker_scale']
            self.svg.create_simple_marker(marker[0], marker[1],
                                          self._styles[marker[2]],
                                          transform, replace=True)
        # Toolmark half lines that will be used to create tangent tool outline.
        self.toolmarks_side_A = []
        self.toolmarks_side_B = []
        # Location of last toolmark (as a point tuple)
        # This is used to reject toolmarks that would be too close together
        self.last_toolmark = None
        # Non-offset tangent lines - used to make offset lines
        self.tan_lines = []

    def plot_move(self, endp):
        """Plot G00 - rapid move from current position to :endp:(x,y,z,a)."""
        self.svg.create_line(self._current_xy, endp, self._styles['moveline'])
        self._update_location(endp)

    def plot_feed(self, endp):
        """Plot G01 - linear feed from current position to :endp:(x,y,z,a)."""
        if self._current_xy.distance(endp) > geom.const.EPSILON:
            if self.tool_layer is not None:
                self._draw_tool_marks(geom.Line(self._current_xy, endp),
                                      start_angle=self._current_a,
                                      end_angle=endp[3])
            self.svg.create_line(self._current_xy, endp,
                                 self._styles['feedline'])
        self._update_location(endp)

    def plot_arc(self, center, endp, clockwise):
        """Plot G02/G03 - arc feed from current position to :endp:(x,y,z,a)."""
        center = geom.P(center)
        radius = center.distance(self._current_xy)
#         assert(self.gcgen.float_eq(center.distance(endp), radius))
        if not self.gcgen.float_eq(center.distance(endp), radius):
            logging.getLogger(__name__).debug(
                'Degenerate arc: d1=%f, d2=%f', center.distance(endp), radius)

        # Draw the tool marks
        if self.tool_layer is not None:
            angle = center.angle2(self._current_xy, endp)
            arc = geom.Arc(self._current_xy, endp, radius, angle, center)
            self._draw_tool_marks(arc, self._current_a, endp[3])

        # Draw the tool path
        sweep_flag = 0 if clockwise else 1
#         style = self._styles['feedarc' + str(sweep_flag)]
        style = self._styles['feedarc']
        self.svg.create_circular_arc(self._current_xy, endp, radius,
                                     sweep_flag, style)
        self._update_location(endp)

    def plot_tool_down(self):
        """Plot the beginning of a tool path.
        """
#        logger.debug('tool down')
#        geom.debug.draw_point(self._current_xy, color='#00ff00')
        self.toolmarks_side_A = []
        self.toolmarks_side_B = []
        self.tan_lines = []
        self.last_toolmark = None

    def plot_tool_up(self):
        """Plot the end of a tool path.
        """
#        logger.debug('tool up')
#        geom.debug.draw_point(self._current_xy, color='#ff0000')
        # Just finish up by drawing the approximate tool path outline.
        if self.show_tm_outline and self.tool_layer is not None:
            self._draw_toolmark_outline()
        if self.x_subpath_render:
            self._draw_subpaths()

    def _draw_tool_marks(self, segment, start_angle, end_angle):
        """Draw marks showing the angle and travel of the tangential tool."""
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
        # This will be the midpoint of the tool mark.
        p = segment.point_at(u)
        if self.last_toolmark is not None and self.last_toolmark.distance(p) < self.toolmark_line_interval / 2:
            return
        self.last_toolmark = p
        if not self.gcgen.float_eq(self.tool_offset, 0.0):
            # Calculate and draw the tool offset mark.
            px = p + geom.P.from_polar(self.tool_offset, angle - math.pi)
            if self.show_toolmarks:
                self.svg.create_line(p, px, self._styles['tooloffset'],
                                     parent=self.tool_layer)
        else:
            # No tool offset
            px = p
        if self.tool_width > self.gcgen.tolerance:
            # Calculate the endpoints of the tool mark.
            r = self.tool_width / 2
            p1 = px + geom.P.from_polar(r, angle + math.pi / 2)
            p2 = px + geom.P.from_polar(r, angle - math.pi / 2)
            if self.show_toolmarks:
                self.svg.create_line(p1, p2, self._styles['toolmark'],
                                     parent=self.tool_layer)
            self.tan_lines.append(geom.Line(p1, p2))
            # Save the half lines to create outline.
            tm_line_A = geom.Line(px, p1)
            tm_line_B = geom.Line(px, p2)
            self.toolmarks_side_A.append(tm_line_A)
            self.toolmarks_side_B.append(tm_line_B)

    def _draw_toolmark_outline(self):
        """Draw an approximation of the tangent toolpath outline.
        """
        if not self.toolmarks_side_A or not self.toolmarks_side_B:
            return
        # TODO: add non-g1 hints at outline cusps
        _unused, p2s_A = zip(*self.toolmarks_side_A)
        _unused, p2s_B = zip(*list(reversed(self.toolmarks_side_B)))
        points_A = list(p2s_A)
        points_B = list(p2s_B)
        side_A = self._make_outline_path(points_A)
        side_B = self._make_outline_path(points_B)
        if not side_A or not side_B:
            return
        side_A = geom.bezier.smooth_path(side_A)
        side_B = geom.bezier.smooth_path(side_B)
        outline = []
        outline.extend(side_A)
        outline.append(geom.Line(side_A[-1].p2, side_B[0].p1))
        outline.extend(side_B)
        style = self._styles['toolmark_outline']
        self.svg.create_polypath(outline, close_path=True, style=style,
                                 parent=self.tool_layer)

    def _draw_subpaths(self):
        """Experimental: Create some offset paths
        """
        if not self.tan_lines:
            return
        if self.x_subpath_layer is None:
            self.x_subpath_layer = self.svg.create_layer(
                                self.x_subpath_layer_name,
                                incr_suffix=self.incr_layer_suffix,
                                flipy=True)
        offset = self.x_subpath_offset
        # All toolmark lines are the same length, so use the first one
        length = self.tan_lines[0].length()
        while offset < length:
            offset_pts = []
            for line in self.tan_lines:
                p = line.point_at(offset / line.length())
                offset_pts.append(p)
            path = self._make_outline_path(offset_pts)
            path = geom.bezier.smooth_path(path,
                                           smoothness=self.x_subpath_smoothness)
            self.svg.create_polypath(path, style=self._styles['subpath'],
                                     parent=self.x_subpath_layer)
            offset += self.x_subpath_offset

    def _make_outline_path(self, points):
        path = []
        if len(points) > 1:
            prev_pt = points[0]
            for next_pt in points[1:]:
                if next_pt != prev_pt:
                    outline = geom.Line(prev_pt, next_pt)
                    path.append(outline)
                prev_pt = next_pt
            path = self._fix_intersections(path)
            path = self._fix_reversals(path)
        return path

    def _fix_intersections(self, path):
        """Collapse self-intersecting loops.
        """
        # See: https://en.wikipedia.org/wiki/Bentley-Ottmann_algorithm
        # for a more efficient sweepline method O(Nlog(N)).
        # This is the bonehead way: O(n**2), but it's fine for
        # reasonable path lengths...
        fixed_path = []
        skip_ahead = 0
        for i, line1 in enumerate(path):
            if i < skip_ahead:
                continue
            p = None
            for j, line2 in enumerate(path[(i + 2):]):
                p = line1.intersection(line2, segment=True)
                if p is not None:
                    fixed_path.append(geom.Line(line1.p1, p))
                    fixed_path.append(geom.Line(p, line2.p2))
                    skip_ahead = i + j + 3
                    break
            if p is None:
                fixed_path.append(line1)
        return fixed_path

    def _fix_reversals(self, path):
        """Collapse path reversals.
        This is when the next segment direction is more than 90deg from
        current segment direction...
        """
        # This works in O(n) time...
        skip_ahead = 0
        line1 = path[0]
        fixed_path = []
        for i, line2 in enumerate(path[1:]):
            if i < skip_ahead:
                continue
            skip_ahead = 0
            angle = line1.p2.angle2(line1.p1, line2.p2)
            if abs(angle) < math.pi / 2:
                if angle > 0:
                    # right turn. corner is poking outwards.
#                    geom.debug.draw_point(line1.p2, color='#0000ff')
                    # Move forward until next reversal
                    for j, line2 in enumerate(path[(i + 1):]):
                        angle = line1.p2.angle2(line1.p1, line2.p2)
                        if abs(angle) > math.pi / 2:
#                            geom.debug.draw_line(line2, color='#ff0000')
                            line2 = geom.Line(line1.p2, line2.p2)
                            skip_ahead = i + j + 1
                            break
                else:
                    # left turn. corner is poking inwards.
#                    geom.debug.draw_point(line1.p2, color='#ff0000')
                    # Move forward until next reversal
                    for j, line2 in enumerate(path[(i + 1):]):
                        line1 = geom.Line(line1.p1, line2.p1)
                        angle = line1.p2.angle2(line1.p1, line2.p2)
                        if abs(angle) > math.pi / 2:
                            skip_ahead = i + j + 1
                            break
            fixed_path.append(line1)
            line1 = line2
        fixed_path.append(line1)
        return fixed_path

    def _update_location(self, endp):
        self._current_xy = geom.P(endp[0], endp[1])
        self._current_z = endp[2]
        self._current_a = endp[3]

