#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
Create vertical and or horizontal lines.

This can be invoked as an Inkscape extension or from the command line.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division, unicode_literals)
# Uncomment this if any of these builtins are used.
# from future_builtins import (ascii, filter, hex, map, oct, zip)

import logging
import gettext
_ = gettext.gettext

from inkscape import inkext
import geom

logger = logging.getLogger(__name__)

class Lines(inkext.InkscapeExtension):
    """"""
    OPTIONSPEC = (
        inkext.ExtOption('--line-orient', type='string', default='h',
                         help='Line orientation'),
        inkext.ExtOption('--line-spacing', type='docunits', default=1.0,
                         help='Line spacing'),
        inkext.ExtOption('--line-angle', type='float', default=0.0,
                         help='Line angle'),
        inkext.ExtOption('--line-left2right', type='inkbool', default=True,
                         help='Draw left to right'),
        inkext.ExtOption('--line-top2bottom', type='inkbool', default=True,
                         help='Draw top to bottom'),
        inkext.ExtOption('--line-double', type='inkbool', default=True,
                         help='Double line'),
        inkext.ExtOption('--line-alt', type='inkbool', default=False,
                         help='Alternate line direction'),
        inkext.ExtOption('--line-skip', type='int', default=1,
                         help='Skip lines'),
        inkext.ExtOption('--line-start', type='int', default=2,
                         help='Start lines at'),

        inkext.ExtOption('--spacing-jitter', type='int', default=0,
                         help='Spacing jitter'),
        inkext.ExtOption('--angle-jitter', type='int', default=0,
                         help='Angle jitter'),


        inkext.ExtOption('--brush-size', type='docunits', default=1.0,
                         help='Brush size'),
        inkext.ExtOption('--brush-overlap', type='docunits', default=0.125,
                         help='Brush overlap'),

        inkext.ExtOption('--margin-left', type='docunits', default=0.0,
                         help='Left margin'),
        inkext.ExtOption('--margin-right', type='docunits', default=0.0,
                         help='Right margin'),
        inkext.ExtOption('--margin-top', type='docunits', default=0.0,
                         help='Top margin'),
        inkext.ExtOption('--margin-bottom', type='docunits', default=0.0,
                         help='Bottom margin'),
    )

    _LAYER_NAME = 'lines'
    _LINE_STYLE = 'fill:none;stroke:#c0c0ff;stroke-width:%.3f;stroke-opacity:.75'

    def run(self):
        """Main entry point for Inkscape plugins.
        """
        doc_size = geom.P(self.svg.get_document_size())
        bottom_left = geom.P(self.options.margin_left,
                             self.options.margin_bottom)
        top_right = doc_size - geom.P(self.options.margin_right,
                                      self.options.margin_top)
        self.margins = geom.box.Box(bottom_left, top_right)

        self.line_layer = self.svg.create_layer(self._LAYER_NAME,
                                                incr_suffix=True, flipy=True)

        line_width = self.options.brush_size
        if line_width == 0.0:
            line_width = self.svg.unit2uu('1px')
        if self.options.brush_size > 0.0:
            line_spacing = self.options.brush_size - self.options.brush_overlap
        else:
            line_spacing = self.options.line_spacing
        self.line_style = self._LINE_STYLE % line_width
        if self.options.line_orient == 'h':
            self.generate_horizontal_lines(line_spacing)
        else:
            self.generate_vertical_lines(line_spacing)

    def generate_horizontal_lines(self, line_spacing):
        if self.options.line_top2bottom:
            line_offset = self.margins.ymax - (self.options.brush_size / 2)
            if self.options.brush_overlap > 0:
                line_offset += self.options.brush_overlap
            line_spacing = -line_spacing
        else:
            line_offset = self.margins.ymin + (self.options.brush_size / 2)
            if self.options.brush_overlap > 0:
                line_offset -= self.options.brush_overlap
        self.render_horizontal_lines(line_offset, line_spacing,
                                    self.options.line_left2right,
                                    self.options.line_alt)

    def render_horizontal_lines(self, line_offset, line_spacing, left2right,
                                alternate):
        line_count = 0
        line_start = self.options.line_start - 1
        line_skip = self.options.line_skip + 1
        while line_offset >= self.margins.ymin and line_offset <= self.margins.ymax:
            if left2right:
                p1 = geom.P(self.margins.xmin, line_offset)
                p2 = geom.P(self.margins.xmax, line_offset)
            else:
                p1 = geom.P(self.margins.xmax, line_offset)
                p2 = geom.P(self.margins.xmin, line_offset)
            if alternate:
                left2right = not left2right
            if line_count >= (line_start - 1) \
            and (line_skip == 1 or (line_count - line_start) % line_skip == 0):
                self.svg.create_line(p1, p2, style=self.line_style,
                                     parent=self.line_layer)
                if self.options.line_double:
                    self.svg.create_line(p2, p1, style=self.line_style,
                                         parent=self.line_layer)
            line_offset += line_spacing
            line_count += 1

    def generate_vertical_lines(self, line_spacing):
        if self.options.line_left2right:
            line_offset = self.margins.xmin + (self.options.brush_size / 2)
            if self.options.brush_overlap > 0:
                line_offset -= self.options.brush_overlap
        else:
            line_offset = self.margins.xmax - (self.options.brush_size / 2)
            line_spacing = -line_spacing
            if self.options.brush_overlap > 0:
                line_offset += self.options.brush_overlap
        self.render_vertical_lines(line_offset, line_spacing,
                                   self.options.line_top2bottom,
                                   self.options.line_alt)

    def render_vertical_lines(self, line_offset, line_spacing, top2bottom,
                              alternate):
        line_count = 0
        line_start = self.options.line_start - 1
        line_skip = self.options.line_skip + 1
        while line_offset >= self.margins.xmin and line_offset <= self.margins.xmax:
            if top2bottom:
                p1 = geom.P(line_offset, self.margins.ymax)
                p2 = geom.P(line_offset, self.margins.ymin)
            else:
                p1 = geom.P(line_offset, self.margins.ymin)
                p2 = geom.P(line_offset, self.margins.ymax)
            if alternate:
                top2bottom = not top2bottom
            if line_count >= (line_start - 1) \
            and (line_skip == 1 or (line_count - line_start) % line_skip == 0):
                self.svg.create_line(p1, p2, style=self.line_style,
                                     parent=self.line_layer)
                if self.options.line_double:
                    self.svg.create_line(p2, p1, style=self.line_style,
                                         parent=self.line_layer)
            line_offset += line_spacing
            line_count += 1

    def clip_to_margins(self, line):
        """
        Returns:
            A clipped line or None if the line lies completely outside the
            margins.
        """
        dx = line.p2.x - line.p1.x
        dy = line.p2.y - line.p1.y
        # Vertical line ?
        if geom.const.is_zero(dx):
            # Line outside of clip rect ?
            if (min(self.p1.x, self.p2.x) < self.margins.xmin
                    or max(self.p1.x, self.p2.x) > self.margins.xmax):
                return None
            p1 = geom.P(self.p1.x, self.ymin)
            p2 = geom.P(self.p1.x, self.ymax)
            if dx < 0: # line goes from top to bottom
                return geom.Line(p2, p1)
            else:
                return geom.Line(p1, p2)
        # Horizontal line ?
        if geom.const.is_zero(dy):
            # Line outside of clip rect ?
            if (min(self.p1.y, self.p2.y) < self.margins.ymin
                    or max(self.p1.y, self.p2.y) > self.margins.ymax):
                return None
            p1 = geom.P(self.xmin, self.p1.y)
            p2 = geom.P(self.xmax, self.p1.y)
            if dy < 0: # line goes from right to left
                return geom.Line(p2, p1)
            else:
                return geom.Line(p1, p2)

        m, b = line.slope_intercept()
        x1 = self.xmin
        y1 = m * x1 + b
        x2 = self.xmax
        y2 = m * x2 + b
        return self.margins.clip_line(geom.Line(geom.P(x1, y1), geom.P(x2, y2)))


if __name__ == '__main__':
    Lines().main(Lines.OPTIONSPEC)
