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
import random
import itertools
import logging
import gettext
_ = gettext.gettext

import geom.fillet
from geom import transform2d
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
        inkext.ExtOption('--hline-connect', type='inkbool', default=False,
                         help=_('Connect lines')),
        inkext.ExtOption('--hline-skip', type='int', default=1,
                         help=_('Skip lines')),
        inkext.ExtOption('--hline-start', type='int', default=2,
                         help=_('Start lines at')),

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
        inkext.ExtOption('--vline-connect', type='inkbool', default=False,
                         help=_('Connect lines')),
        inkext.ExtOption('--vline-skip', type='int', default=1,
                         help=_('Skip lines')),
        inkext.ExtOption('--vline-start', type='int', default=2,
                         help=_('Start lines at')),

        inkext.ExtOption('--css-default', type='inkbool', default=False,
                         help=_('Use default CSS (black, 1pt, 100%)')),
        inkext.ExtOption('--h-stroke-width', type='docunits', default=1.0,
                         help=_('Line stroke width')),
        inkext.ExtOption('--h-stroke-opacity', type='float', default=1.0,
                         help=_('Line stroke opacity')),
        inkext.ExtOption('--h-stroke', type='string', default='#000000',
                         help=_('Line stroke color')),

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
        inkext.ExtOption('--line-fillet', type='inkbool', default=False,
                         help=_('Fillet connected lines')),
        inkext.ExtOption('--line-fillet-radius', type='docunits', default=0.0,
                         help=_('Fillet radius')),

        inkext.ExtOption('--hline-vline', type='inkbool', default=False,
                         help=_('Alternate horizontal and vertical lines')),
        inkext.ExtOption('--hv-shuffle', type='inkbool', default=False,
                         help=_('Shuffle alternating lines')),
        inkext.ExtOption('--disable-jitter', type='inkbool', default=False,
                         help=_('Disable jitter')),
        inkext.ExtOption('--spacing-jitter', type='int', default=0,
                         help=_('Line spacing jitter (0-100% of spacing)')),
        inkext.ExtOption('--angle-jitter', type='degrees', default=0,
                         help=_('Maximum line angle jitter (degrees)')),
        inkext.ExtOption('--angle-kappa', type='float', default=2,
                         help=_('Angle jitter concentration (kappa)')),


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

    _LAYER_NAME = 'Grid lines'
    _LAYER_NAME_H = 'Grid lines (H)'
    _LAYER_NAME_V = 'Grid lines (V)'
    _LINE_STYLE = 'fill:none;stroke:%s;stroke-width:%.3f;stroke-opacity:%.2f'
    _MIN_OPACITY = 0.1

    _styles = {
        'h_line':
            'fill:none;stroke-linejoin:round;'
            'stroke:$h_stroke;stroke-width:$h_stroke_width;'
            'stroke-opacity:$h_stroke_opacity;',
        'v_line':
            'fill:none;stroke-linejoin:round;'
            'stroke:$v_stroke;stroke-width:$v_stroke_width;'
            'stroke-opacity:$v_stroke_opacity;',
    }
    _style_defaults = {
        'h_stroke': '#c0c0c0',
        'h_stroke_width': '1pt',
        'h_stroke_opacity': '1',
        'v_stroke': '#c0c0c0',
        'v_stroke_width': '1pt',
        'v_stroke_opacity': '1',
    }

    def run(self):
        """Main entry point for Inkscape plugins.
        """
        geom.debug.set_svg_context(self.debug_svg)

        if not self.options.css_default:
            color =  css.csscolor_to_cssrgb(self.options.h_stroke)      
            self.options.h_stroke = color
            if self.options.h_stroke_width == 0:
                self.options.h_stroke_width = self.svg.unit2uu('1pt')
            if self.options.h_stroke_opacity == 0:
                self.options.h_stroke_opacity = self._MIN_OPACITY
            if self.options.vline_copycss:
                self.options.v_stroke = self.options.h_stroke
                self.options.v_stroke_width = self.options.h_stroke_width
                self.options.v_stroke_opacity = self.options.h_stroke_opacity
            else:
                color = css.csscolor_to_cssrgb(self.options.v_stroke)
                self.options.v_stroke = color
                if self.options.v_stroke_width == 0:
                    self.options.v_stroke_width = self.svg.unit2uu('1pt')
                if self.options.h_stroke_opacity == 0:
                    self.options.h_stroke_opacity = self._MIN_OPACITY
            option_styles = vars(self.options)
        else:
            option_styles = None
                
        # Update styles with any command line option values
        self._styles.update(self.svg.styles_from_templates(
            self._styles, self._style_defaults, option_styles))

        self.cliprect = self.svg.margin_cliprect(self.options.margin_top,
                                                 self.options.margin_right,
                                                 self.options.margin_bottom,
                                                 self.options.margin_left)
        
        # Jitter is expressed as a percentage of max jitter.
        # Max jitter is 50% of line spacing.
        self.options.spacing_jitter /= 100
        
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

        if not self.options.hline_vline:
            # Connect the lines to create continuous paths
            if self.options.hline_connect:
                hlines = self.insert_connectors(hlines)
            if self.options.vline_connect:
                vlines = self.insert_connectors(vlines)
            # TODO: See if it makes sense to then connect the two paths
        
        # Create polypaths
        hpaths = self.connected_paths(hlines)
        vpaths = self.connected_paths(vlines)
        
        # Create SVG layer(s)
        if ((not self.options.grid_layers)
            or (self.options.hline_vline and hlines and vlines)):
            h_layer = self.svg.create_layer(self._LAYER_NAME,
                                             incr_suffix=True, flipy=True)
            v_layer = h_layer
        else:
            if hlines:
                h_layer = self.svg.create_layer(self._LAYER_NAME_H,
                                                incr_suffix=True, flipy=True)
            if vlines:
                v_layer = self.svg.create_layer(self._LAYER_NAME_V,
                                                incr_suffix=True, flipy=True)
            
        if self.options.hline_vline and hlines and vlines:
            # Optionally shuffle the path order.
            if self.options.hv_shuffle:
                random.shuffle(hpaths)
                random.shuffle(vpaths)
            # Draw horizontal alternating with vertical grid lines
            for hpath, vpath in itertools.izip_longest(hpaths, vpaths):
                if hpath is not None:
                    self.svg.create_polypath(hpath,
                                             style=self._styles['h_line'],
                                             parent=h_layer)
                if vpath is not None:
                    self.svg.create_polypath(vpath,
                                             style=self._styles['v_line'],
                                             parent=h_layer)
        else:
            if hlines:
                self.render_lines(hpaths, style=self._styles['h_line'],
                                  layer=h_layer)
            if vlines:
                self.render_lines(vpaths, style=self._styles['v_line'],
                                  layer=v_layer)
                
    def connected_paths(self, lines):
        """ Make paths from connected lines
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
#                 logger.debug('pathlen: %d' % len(path))
                path = [line,]
        if path:
            paths.append(path)
        return paths

    def render_lines(self, paths, style, layer):
        """ Render line paths as SVG
        """
        for path in paths:
            if len(path) == 1:
                self.svg.create_line(path[0].p1, path[0].p2,
                                     style=style, parent=layer)
            elif path:
                if self.options.line_fillet:
                    radius = self.options.line_fillet_radius
                    path = geom.fillet.fillet_path(path, radius,
                                                   fillet_close=False)
                self.svg.create_polypath(path, style=style, parent=layer)
        
    def insert_connectors(self, lines):
        """
        """
        connected_lines = []
        prev_line = None
        for line in lines:
            if prev_line is not None and prev_line.p2 != line.p1:
                connectors = self._connect_lines(prev_line, line)
                connected_lines.extend(connectors)
            prev_line = line
            connected_lines.append(line)
        return connected_lines
        
    def make_lines(self, spacing, line_rotation, reverse_path,
                   reverse_order, alternate, doubled):
        """
        """
        # Rotation angle should be > -math.pi and < math.pi
        line_rotation = geom.normalize_angle(line_rotation, center=0.0)
        quadrant = abs(line_rotation) + (math.pi / 4)
        if math.pi/2 < quadrant and quadrant < math.pi:
            # Lines are vertically oriented
            return self.make_vlines(spacing, line_rotation,
                                    reverse_path, reverse_order,
                                    alternate, doubled)
        else:
            return self.make_hlines(spacing, line_rotation,
                                    reverse_path, reverse_order,
                                    alternate, doubled)

    def make_hlines(self, spacing, line_rotation, reverse_path,
                    reverse_order, alternate, doubled):
        """ Generate horizontal lines
        """
        # Adjust axis-aligned spacing to compensate for rotated normal 
        if not geom.is_zero(line_rotation):
            spacing = spacing / math.cos(line_rotation)
        dx = self.cliprect.width()
        dy = abs(math.tan(line_rotation) * dx)
        maxlines = int((self.cliprect.height() + dy) / spacing) + 1
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
        return self._create_lines(start_line, maxlines, spacing,
                                  alternate, doubled, 0, 1)


    def make_vlines(self, spacing, line_rotation, reverse_path,
                    reverse_order, alternate, doubled):
        """ Generate vertical lines
        """
        # Adjust axis-aligned spacing to compensate for rotated normal
        if not geom.is_zero(line_rotation):
            spacing = spacing / math.sin(line_rotation)
        # Re-canonicalize the rotation angle (relative to vertical axis)
        line_rotation -= math.pi/2
        dy = self.cliprect.height()
        dx = abs(math.tan(line_rotation) * dy)
        maxlines = int((self.cliprect.width() + dx) / spacing) + 1
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
        return self._create_lines(start_line, maxlines, spacing,
                                  alternate, doubled, 1, 0)

    def _create_lines(self, start_line, maxlines, spacing,
                      alternate, doubled, x, y):
        # Extend the start line to provide some headroom for clipping
        # possibly rotated line segments. This is a hack to compensate
        # for the lack of infinite line clipping in Box...
        # TODO: implement infinite line clipping...
        start_line = start_line.extend(self.cliprect.diagonal(), from_midpoint=True)
        lines = []
        offset = 0
        for i in range(maxlines):
            offset = self._spacing_offset(offset, spacing, i, maxlines)
            line = geom.Line(start_line + (x * offset, y * offset))
            if (i % 2) > 0 and alternate:
                # Alternate the path direction every other line
                line = line.reversed()
            # Add rotational jitter or offset if any
            line = self._rotate_line(line, i, maxlines)
            segment = self.cliprect.clip_line(line)
            if segment is not None:
                lines.append(segment)
                if doubled:
                    segment2 = geom.Line(segment.p2, segment.p1)
                    lines.append(segment2)
        return lines

    def _connect_lines(self, line1, line2):
        """
        """
        # The following mess takes care of literal corner cases
        # where the connection would be between two lines on either
        # side of a clip rect corner.
        # There's probably a simpler way to deal with this...
        pp1 = geom.P(line1.p2.x, line2.p1.y)
        pp2 = geom.P(line2.p1.x, line1.p2.y)
        pc = None
        if (pp1 == self.cliprect.p1 or pp2 == self.cliprect.p1):
            pc = self.cliprect.p1
        elif (pp1 == self.cliprect.topleft or pp2 == self.cliprect.topleft):
            pc = self.cliprect.topleft
        elif (pp1 == self.cliprect.p2 or pp2 == self.cliprect.p2):
            pc = self.cliprect.p2
        elif (pp1 == self.cliprect.bottomright or pp2 == self.cliprect.bottomright):
            pc = self.cliprect.bottomright
        if pc is not None:
            return (geom.Line(line1.p2, pc), geom.Line(pc, line2.p1))
        else:
            return (geom.Line(line1.p2, line2.p1),)

    def _spacing_offset(self, current_offset, spacing, linenum, _maxlines):
        """
        """
        if linenum == 0:
            spacing = 0
        if not self.options.disable_jitter and self.options.spacing_jitter > 0:
            mu = 0
            sigma = 0.4
            jitter_scale = random.normalvariate(mu, sigma) / 2
            spacing += jitter_scale * self.options.spacing_jitter * spacing
        return current_offset + spacing

    def _rotate_line(self, line, _linenum, _maxlines):
        """
        """
        if self.options.disable_jitter or self.options.angle_jitter > 0:
            return line
        # This produces a random angle between -pi and pi
        kappa = self.options.angle_kappa
        norm_angle = random.vonmisesvariate(math.pi, kappa) - math.pi
        jitter_angle = norm_angle * self.options.angle_jitter / math.pi
        if not geom.is_zero(jitter_angle):
            mat = transform2d.matrix_rotate(jitter_angle,
                                            origin=line.midpoint())
            line = line.transform(mat)
        return line
        
    def _nonlinear_spacing(self, spacing, linenum, maxlines):
        """
        """
#         mult = abs(spacing) / math.log(maxlines)
#         offset = linenum * spacing# * math.log(linenum + 1) * mult
        
        
if __name__ == '__main__':
    Lines().main(Lines.OPTIONSPEC)
