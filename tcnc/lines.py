#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
Create vertical and or horizontal lines.
This is mainly for creating grids for CNC output.

This can be invoked as an Inkscape extension or from the command line.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division, unicode_literals)
# Uncomment this if any of these builtins are used.
# from future_builtins import (ascii, filter, hex, map, oct, zip)

import math
import logging
import gettext
_ = gettext.gettext

import geom
from inkscape import inkext
from svg import css


logger = logging.getLogger(__name__)

class Lines(inkext.InkscapeExtension):
    """"""
    OPTIONSPEC = (
        inkext.ExtOption('--hline-draw', type='inkbool', default=False,
                         help=_('Draw horizontal lines')),
        inkext.ExtOption('--hline-spacing', type='docunits', default=1.0,
                         help=_('Line spacing center to center')),
        inkext.ExtOption('--hline-rotation', type='degrees', default=0.0,
                         help=_('Line rotation')),
        inkext.ExtOption('--hline-right2left', type='inkbool', default=False,
                         help=_('Direction left to right')),
        inkext.ExtOption('--hline-top2bottom', type='inkbool', default=True,
                         help=_('Order top to bottom')),
        inkext.ExtOption('--hline-double', type='inkbool', default=True,
                         help=_('Double line')),
        inkext.ExtOption('--hline-alt', type='inkbool', default=False,
                         help=_('Alternate line direction')),
        inkext.ExtOption('--hline-skip', type='int', default=1,
                         help=_('Skip lines')),
        inkext.ExtOption('--hline-start', type='int', default=2,
                         help=_('Start lines at')),

        inkext.ExtOption('--h-stroke-width', type='docunits', default=1.0,
                         help=_('Line stroke width')),
        inkext.ExtOption('--h-stroke-opacity', type='float', default=1.0,
                         help=_('Line stroke opacity')),
        inkext.ExtOption('--h-stroke', type='string', default='#000000',
                         help=_('Line stroke color')),

        inkext.ExtOption('--vline-draw', type='inkbool', default=False,
                         help=_('Draw vertical lines')),
        inkext.ExtOption('--vline-spacing', type='docunits', default=1.0,
                         help=_('Line spacing center to center')),
        inkext.ExtOption('--vline-rotation', type='degrees', default=0.0,
                         help=_('Line rotation')),
        inkext.ExtOption('--vline-right2left', type='inkbool', default=False,
                         help=_('Direction left to right')),
        inkext.ExtOption('--vline-top2bottom', type='inkbool', default=True,
                         help=_('Order top to bottom')),
        inkext.ExtOption('--vline-double', type='inkbool', default=True,
                         help=_('Double line')),
        inkext.ExtOption('--vline-alt', type='inkbool', default=False,
                         help=_('Alternate line direction')),
        inkext.ExtOption('--vline-skip', type='int', default=1,
                         help=_('Skip lines')),
        inkext.ExtOption('--vline-start', type='int', default=2,
                         help=_('Start lines at')),

        inkext.ExtOption('--vline-copycss', type='inkbool', default=False,
                         help=_('Use same CSS settings as horizontal lines')),
        inkext.ExtOption('--v-stroke-width', type='docunits', default=1.0,
                         help=_('Line stroke width')),
        inkext.ExtOption('--v-stroke-opacity', type='float', default=1.0,
                         help=_('Line stroke opacity')),
        inkext.ExtOption('--v-stroke', type='string', default='#000000',
                         help=_('Line stroke color')),

        inkext.ExtOption('--grid-layers', type='inkbool', default=False,
                         help=_('One layer per grid part (horizontal, vertical)')),
        inkext.ExtOption('--line-connect', type='inkbool', default=False,
                         help=_('Connect lines')),
        inkext.ExtOption('--line-connect-type', type='string', default='0',
                         help=_('Line connection type')),

        inkext.ExtOption('--hline-vline', type='inkbool', default=False,
                         help=_('Alternate horizontal and vertical lines')),
        inkext.ExtOption('--interval-jitter', type='int', default=0,
                         help=_('Interval jitter')),
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

        inkext.ExtOption('--margin-left', type='docunits', default=0.0,
                         help=_('Left margin')),
        inkext.ExtOption('--margin-right', type='docunits', default=0.0,
                         help=_('Right margin')),
        inkext.ExtOption('--margin-top', type='docunits', default=0.0,
                         help=_('Top margin')),
        inkext.ExtOption('--margin-bottom', type='docunits', default=0.0,
                         help=_('Bottom margin')),
    )

    _LAYER_NAME_H = 'Grid lines H'
    _LAYER_NAME_V = 'Grid lines V'
    _LINE_STYLE = 'fill:none;stroke:%s;stroke-width:%.3f;stroke-opacity:%.2f'

    _styles = {
        'v_line':
            'fill:none;stroke-linejoin:round;'
            'stroke:$v_stroke;stroke-width:$v_stroke_width;'
            'stroke-opacity:$v_stroke_opacity;',
        'h_line':
            'fill:none;stroke-linejoin:round;'
            'stroke:$h_stroke;stroke-width:$h_stroke_width;'
            'stroke-opacity:$h_stroke_opacity;',
    }
    _style_defaults = {
        'v_stroke': '#000000',
        'v_stroke_width': '1pt',
        'v_stroke_opacity': '.75',
        'h_stroke': '#000000',
        'h_stroke_width': '1pt',
        'h_stroke_opacity': '.75',
    }

    def run(self):
        """Main entry point for Inkscape plugins.
        """
        self.options.h_stroke = css.csscolor_to_cssrgb(self.options.h_stroke)
        self.options.v_stroke = css.csscolor_to_cssrgb(self.options.v_stroke)
        if self.options.h_stroke_width == 0:
            self.options.h_stroke_width = self.svg.unit2uu('1pt')
        if self.options.v_stroke_width == 0:
            self.options.v_stroke_width = self.svg.unit2uu('1pt')
        # Update styles with any command line option values
        self._styles.update(self.svg.styles_from_templates(
            self._styles, self._style_defaults, vars(self.options)))

        self.cliprect = self.svg.margin_cliprect(self.options.margin_top,
                                                 self.options.margin_right,
                                                 self.options.margin_bottom,
                                                 self.options.margin_left)
        # Create the grid lines
        hlines = []
        vlines = []
        if self.options.hline_draw:
            hlines = self.make_lines(self.options.hline_spacing,
                                     self.options.hline_rotation,
                                     self.options.hline_right2left,
                                     self.options.hline_top2bottom,
                                     self.options.hline_alt,
                                     self.options.hline_double)
        if self.options.vline_draw:
            vlines = self.make_lines(self.options.vline_spacing,
                                     self.options.vline_rotation + math.pi / 2,
                                     self.options.vline_top2bottom,
                                     self.options.vline_right2left,
                                     self.options.vline_alt,
                                     self.options.vline_double)        
        # Connect the lines
        if self.options.line_connect:
            hlines = self.insert_connectors(hlines)
            vlines = self.insert_connectors(vlines)
        
        # Create layers with origin at lower left
        h_layer = self.svg.create_layer(self._LAYER_NAME_H,
                                        incr_suffix=True, flipy=True)
        if self.options.grid_layers:
            v_layer = self.svg.create_layer(self._LAYER_NAME_V,
                                            incr_suffix=True, flipy=True)
        else:
            v_layer = h_layer

        # Render lines as SVG paths
        self.render_lines(hlines, style=self._styles['h_line'], layer=h_layer)
        self.render_lines(vlines, style=self._styles['v_line'], layer=v_layer)
    
    def render_lines(self, lines, style, layer):
        """Convert connected lines to paths
        """
        paths = []
        path = []
        for line in lines:
            if not path:
                path.append(line)
            elif path[-1].p2 == line.p1:
                path.append(line)
            else:
                paths.append(path)
                logger.debug('pathlen: %d' % len(path))
                path = [line,]
        paths.append(path)
        for path in paths:
            if len(path) == 1:
                self.svg.create_line(path[0].p1, path[0].p2,
                                     style=style, parent=layer)
            elif path:
                poly = [path[0].p1]
                for line in path:
                    poly.append(line.p2)
                self.svg.create_polygon(poly, close_polygon=False,
                                        style=style, parent=layer)
        
    def insert_connectors(self, lines):
        """
        """
        connected_lines = []
        prev_line = None
        for line in lines:
            if prev_line is not None and prev_line.p2 != line.p1:
                connector = geom.Line(prev_line.p2, line.p1)
                connected_lines.append(connector)
            prev_line = line
            connected_lines.append(prev_line)
        return connected_lines
        
    def make_lines(self, spacing, line_rotation, right2left,
                   top2bottom, alternate, doubled):
        """
        """
        line_rotation = geom.normalize_angle(line_rotation, center=0.0)
        quadrant = abs(line_rotation) + (math.pi / 4)
        if math.pi/2 < quadrant and quadrant < math.pi:
            # Lines are vertically oriented
            return self.make_vlines(spacing, line_rotation - math.pi/2,
                                    right2left, top2bottom, alternate, doubled)
        else:
            return self.make_hlines(spacing, line_rotation,
                                    right2left, top2bottom, alternate, doubled)

    def make_hlines(self, spacing, line_rotation, reverse_path,
                    reverse_order, alternate, doubled):
        """ Generate horizontal lines
        """
        dx = self.cliprect.width()
        dy = abs(math.tan(line_rotation) * dx)
        numlines = int((self.cliprect.height() + dy) / spacing) + 1
        x1 = self.cliprect.xmin
        x2 = self.cliprect.xmin + dx
        if reverse_path:
            x1, x2 = x2, x1
        y1 = self.cliprect.ymin - dy
        y2 = self.cliprect.ymin
        if reverse_order:
            y_offset = self.cliprect.height() + dy
            y1 += y_offset
            y2 += y_offset
            spacing = -spacing
        if reverse_path == (line_rotation > 0):
            y1, y2 = y2, y1
        start_line = geom.Line((x1, y1), (x2, y2))
        return self._create_lines(start_line, numlines, spacing,
                                  alternate, doubled, 0, 1)


    def make_vlines(self, spacing, line_rotation, reverse_path,
                    reverse_order, alternate, doubled):
        """ Generate vertical lines
        """
        dy = self.cliprect.height()
        dx = abs(math.tan(line_rotation) * dy)
        numlines = int((self.cliprect.width() + dx) / spacing) + 1
        y1 = self.cliprect.ymin
        y2 = self.cliprect.ymin + dy
        if reverse_path:
            y1, y2 = y2, y1
        x1 = self.cliprect.xmin - dx
        x2 = self.cliprect.xmin
        if reverse_order:
            x_offset = self.cliprect.width() + dx
            x1 += x_offset
            x2 += x_offset
            spacing = -spacing
        if reverse_path == (line_rotation < 0):
            x1, x2 = x2, x1
        start_line = geom.Line((x1, y1), (x2, y2))
        return self._create_lines(start_line, numlines, spacing,
                                  alternate, doubled, 1, 0)

    def _create_lines(self, start_line, numlines, spacing,
                      alternate, doubled, x, y):
        lines = []
        for i in range(numlines):
            offset = (x * (i * spacing), y * (i * spacing))
            line = self.cliprect.clip_line(geom.Line(start_line + offset))
            if line is not None:
                if (i % 2) > 0 and alternate:
                    # Alternate the path direction every other line
                    line = line.reversed()
                lines.append(line)
                if doubled:
                    line2 = geom.Line(line.p2, line.p1)
                    lines.append(line2)
        return lines


if __name__ == '__main__':
    Lines().main(Lines.OPTIONSPEC)
