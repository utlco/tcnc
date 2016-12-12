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
                         help=_('Line orientation')),
        inkext.ExtOption('--line-spacing', type='docunits', default=1.0,
                         help=_('Line spacing')),
        inkext.ExtOption('--line-angle', type='float', default=0.0,
                         help=_('Line angle')),
        inkext.ExtOption('--line-left2right', type='inkbool', default=True,
                         help=_('Direction left to right')),
        inkext.ExtOption('--line-top2bottom', type='inkbool', default=True,
                         help=_('Order top to bottom')),
        inkext.ExtOption('--line-double', type='inkbool', default=True,
                         help=_('Double line')),
        inkext.ExtOption('--line-alt', type='inkbool', default=False,
                         help=_('Alternate line direction')),
        inkext.ExtOption('--line-skip', type='int', default=1,
                         help=_('Skip lines')),
        inkext.ExtOption('--line-start', type='int', default=2,
                         help=_('Start lines at')),

        inkext.ExtOption('--spacing-jitter', type='int', default=0,
                         help=_('Spacing jitter')),
        inkext.ExtOption('--angle-jitter', type='int', default=0,
                         help=_('Angle jitter')),


        inkext.ExtOption('--sine-line', type='inkbool', default=False,
                         help=_('Draw lines as sine waves')),
        inkext.ExtOption('--sine-start-wavelength', type='float', default=1,
                         help=_('Starting wavelength')),
        inkext.ExtOption('--sine-end-wavelength', type='float', default=1,
                         help=_('Ending wavelength')),
        inkext.ExtOption('--sine-start-amplitude', type='float', default=0,
                         help=_('Starting amplitude')),
        inkext.ExtOption('--sine-end-amplitude', type='float', default=0,
                         help=_('Ending amplitude')),

        inkext.ExtOption('--brush-size', type='docunits', default=1.0,
                         help=_('Brush size')),
        inkext.ExtOption('--brush-overlap', type='docunits', default=0.125,
                         help=_('Brush overlap')),

        inkext.ExtOption('--margin-left', type='docunits', default=0.0,
                         help=_('Left margin')),
        inkext.ExtOption('--margin-right', type='docunits', default=0.0,
                         help=_('Right margin')),
        inkext.ExtOption('--margin-top', type='docunits', default=0.0,
                         help=_('Top margin')),
        inkext.ExtOption('--margin-bottom', type='docunits', default=0.0,
                         help=_('Bottom margin')),
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
        self.generate_lines(line_spacing)

    def generate_lines(self, line_spacing):
        if self.options.line_top2bottom:
            line_offset = self.margins.ymax - (self.options.brush_size / 2)
            if self.options.brush_overlap > 0:
                line_offset += self.options.brush_overlap
            line_spacing = -line_spacing
        else:
            line_offset = self.margins.ymin + (self.options.brush_size / 2)
            if self.options.brush_overlap > 0:
                line_offset -= self.options.brush_overlap
        self.render_lines(line_offset, line_spacing,
                                    self.options.line_left2right,
                                    self.options.line_alt)

    def render_lines(self, line_offset, line_spacing, left2right,
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

def clip_line_to_margins(self, line, margins):
    """
    Returns:
        A clipped line or None if the line lies completely outside the
        margins.
    """
    dx = line.p2.x - line.p1.x
    dy = line.p2.y - line.p1.y

    # Vertical line ?
    if geom.const.is_zero(dx):
        x = line.p1.x
        # Line outside of clip rect ?
        if x < margins.xmin or x > margins.xmax:
            return None
        elif dy < 0: # line goes from top to bottom
            return geom.Line((x, margins.ymax), (x, margins.ymin))
        else:
            return geom.Line((x, margins.ymin), (x, margins.ymax))

    # Horizontal line ?
    if geom.const.is_zero(dy):
        y = line.p1.y
        # Line outside of clip rect ?
        if y < margins.ymin or y > margins.ymax:
            return None
        elif dx < 0: # line goes from right to left
            return geom.Line((margins.xmax, y), (margins.xmin, y))
        else:
            return geom.Line((margins.xmin, y), (margins.xmax, y))

    m, b = line.slope_intercept()
    x1 = margins.xmin
    x2 = margins.xmax
    if dx < 0: # line goes from right to left
        x1, x2 = x2, x1
    y1 = m * x1 + b
    y2 = m * x2 + b
    return margins.clip_line(geom.Line(geom.P(x1, y1), geom.P(x2, y2)))


if __name__ == '__main__':
    Lines().main(Lines.OPTIONSPEC)
