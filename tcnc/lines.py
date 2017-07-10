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
        inkext.ExtOption('--hline-spacing-jitter', type='int', default=0,
                         help=_('Line spacing jitter (0-100% of spacing)')),
        inkext.ExtOption('--hline-angle-jitter', type='degrees', default=0,
                         help=_('Maximum line angle jitter (degrees)')),
        inkext.ExtOption('--hline-angle-kappa', type='float', default=2,
                         help=_('Angle jitter concentration (kappa)')),
        inkext.ExtOption('--hline-varspacing', type='inkbool', default=False,
                         help=_('Enable variable spacing')),
        inkext.ExtOption('--hline-varspacing-min', type='docunits', default=0,
                         help=_('Minimum line spacing')),
        inkext.ExtOption('--hline-varspacing-max', type='docunits', default=0,
                         help=_('Maximum line spacing')),
        inkext.ExtOption('--hline-varspacing-cycles', type='float', default=1,
                         help=_('Number of cycles')),
        inkext.ExtOption('--hline-varspacing-formula', default='',
                         help=_('Spacing formula')),
        inkext.ExtOption('--hline-varspacing-invert', type='inkbool', default=False,
                         help=_('Invert spacing order')),
        inkext.ExtOption('--hline-rotation', type='degrees', default=0.0,
                         help=_('Line rotation')),
        inkext.ExtOption('--hline-reverse-path', type='inkbool', default=False,
                         help=_('Draw left to right')),
        inkext.ExtOption('--hline-reverse-order', type='inkbool', default=True,
                         help=_('Reverse line order')),
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
        inkext.ExtOption('--vline-spacing-jitter', type='int', default=0,
                         help=_('Line spacing jitter (0-100% of spacing)')),
        inkext.ExtOption('--vline-varspacing', type='inkbool', default=False,
                         help=_('Enable variable spacing')),
        inkext.ExtOption('--vline-varspacing-min', type='docunits', default=0,
                         help=_('Minimum line spacing')),
        inkext.ExtOption('--vline-varspacing-max', type='docunits', default=0,
                         help=_('Maximum line spacing')),
        inkext.ExtOption('--vline-varspacing-cycles', type='float', default=1,
                         help=_('Number of cycles')),
        inkext.ExtOption('--vline-varspacing-formula', default='linear',
                         help=_('Spacing formula')),
        inkext.ExtOption('--vline-varspacing-invert', type='inkbool', default=True,
                         help=_('Invert spacing order')),
        inkext.ExtOption('--vline-rotation', type='degrees', default=0.0,
                         help=_('Line rotation')),
        inkext.ExtOption('--vline-angle-jitter', type='degrees', default=0,
                         help=_('Maximum line angle jitter (degrees)')),
        inkext.ExtOption('--vline-angle-kappa', type='float', default=2,
                         help=_('Angle jitter concentration (kappa)')),
        inkext.ExtOption('--vline-right2left', type='inkbool', default=False,
                         help=_('Direction left to right')),
        inkext.ExtOption('--vline-reverse-path', type='inkbool', default=True,
                         help=_('Order top to bottom')),
        inkext.ExtOption('--vline-reverse-order', type='inkbool', default=True,
                         help=_('Reverse line order')),
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
        inkext.ExtOption('--enable-jitter', type='inkbool', default=False,
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
            color = css.csscolor_to_cssrgb(self.options.h_stroke)
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
            logger.debug('invert0: %s', self.options.hline_varspacing_invert)
            lineset = LineSet(
                        self.cliprect, self.options.hline_spacing,
                        self.options.hline_rotation,
                        spacing_jitter=self.options.hline_spacing_jitter,
                        angle_jitter=self.options.hline_angle_jitter,
                        angle_jitter_kappa=self.options.hline_angle_kappa,
                        spacing_formula=self.options.hline_varspacing_formula,
                        varspace_min=self.options.hline_varspacing_min,
                        varspace_max=self.options.hline_varspacing_max,
                        varspace_cycles=self.options.hline_varspacing_cycles,
                        varspace_invert=self.options.hline_varspacing_invert)
            hlines = lineset.lines
            if self.options.hline_reverse_order:
                hlines.reverse()
            hlines = self.insert_reversed_lines(hlines,
                                                self.options.hline_double,
                                                self.options.hline_reverse_path,
                                                self.options.hline_alt)
        if self.options.vline_draw:
            lineset = LineSet(
                        self.cliprect, self.options.vline_spacing,
                        self.options.vline_rotation + math.pi / 2,
                        spacing_jitter=self.options.vline_spacing_jitter,
                        angle_jitter=self.options.vline_angle_jitter,
                        angle_jitter_kappa=self.options.vline_angle_kappa,
                        spacing_formula=self.options.vline_varspacing_formula,
                        varspace_min=self.options.vline_varspacing_min,
                        varspace_max=self.options.vline_varspacing_max,
                        varspace_cycles=self.options.vline_varspacing_cycles,
                        varspace_invert=self.options.vline_varspacing_invert)
            vlines = lineset.lines
            if self.options.vline_reverse_order:
                vlines.reverse()
            vlines = self.insert_reversed_lines(vlines,
                                                self.options.vline_double,
                                                self.options.vline_reverse_path,
                                                self.options.vline_alt)

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
        if not lines:
            return []
        paths = []
        path = [lines[0]]
        for line in lines[1:]:
            if path[-1].p2 == line.p1:
                path.append(line)
            else:
                paths.append(path)
#                 logger.debug('pathlen: %d' % len(path))
                path = [line]
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

    def insert_reversed_lines(self, lines, doubled, reverse, alternate):
        """
        """
        if not doubled and not reverse:
            return lines
        doubled_lines = []
        linenum = 0
        for line in lines:
            is_odd = (linenum % 2) != 0
#             logger.debug('R: %s, A: %s, O: %s', str(reverse), str(alternate), str(is_odd))
            if ((not reverse and alternate and is_odd)
                    or (reverse and (not alternate or not is_odd))):
                doubled_lines.append(line.reversed())
                if doubled:
                    doubled_lines.append(line)
            else:
                doubled_lines.append(line)
                if doubled:
                    doubled_lines.append(line.reversed())
            linenum += 1
        return doubled_lines

    def insert_connectors(self, lines):
        """
        """
        connected_lines = []
        prev_line = None
        for line in lines:
            if prev_line is not None and prev_line.p2 != line.p1:
                connected_lines.append(geom.Line(prev_line.p2, line.p1))
            prev_line = line
            connected_lines.append(line)
        return connected_lines


class LineSet(object):
    """
    """
    def __init__(self, cliprect, spacing, angle,
                   spacing_jitter=0,
                   angle_jitter=0, angle_jitter_kappa=2,
                   spacing_formula=None,
                   varspace_min=0, varspace_max=0,
                   varspace_cycles=2,
                   varspace_invert=False,
                   ):
        """
        """
        self.cliprect = cliprect
        self.spacing = spacing
        self.spacing_jitter = spacing_jitter
        self.angle_jitter = angle_jitter
        self.angle_jitter_kappa = angle_jitter_kappa
        self.spacing_formula = spacing_formula
        self.varspace_min = varspace_min
        self.varspace_max = varspace_max
        self.varspace_cycles = varspace_cycles
        self.varspace_invert = varspace_invert

        # Normalize the line angle: -pi/2 < angle < pi/2
        # Prototype line vector is always bottom to top, left to right.
        self.angle = geom.normalize_angle(angle, center=0)
        if self.angle > (math.pi / 2):
            self.angle -= math.pi
        elif self.angle < -(math.pi / 2):
            self.angle += math.pi
        # A line that's between 45 and 135 degrees is considered
        # vertically oriented.
        if self.angle > math.pi * .25 and self.angle < math.pi * .75:
            self.is_vertical = True
        else:
            self.is_vertical = False
        logger.debug('angle: %.3f, is_vertical: %s', self.angle, str(self.is_vertical))

        self.axis_spacing = self.spacing
        if not geom.is_zero(self.angle):
            # Adjust axis-aligned spacing to compensate for rotated normal
            if self.is_vertical:
                self.axis_spacing /= math.sin(self.angle)
            else:
                self.axis_spacing /= math.cos(self.angle)

        # Set reasonable defaults for variable spacing extents
        if geom.is_zero(self.varspace_min):
            self.varspace_min = 0.1
        if geom.is_zero(self.varspace_max):
            self.varspace_max = self.axis_spacing

        self.lines = self.make_lines()

    def make_lines(self):
        """ Generate lines.
        """
        if self.is_vertical:
            dx = abs(math.cos(self.angle) * self.cliprect.height())
            max_extent = self.cliprect.width() + dx
            x1 = self.cliprect.xmin - dx
            x2 = self.cliprect.xmin
            y1 = self.cliprect.ymin
            y2 = self.cliprect.ymax
            if self.angle < 0:
                x1, x2 = x2, x1
        else:
            dy = abs(math.sin(self.angle) * self.cliprect.width())
            max_extent = self.cliprect.height() + dy
            x1 = self.cliprect.xmin
            x2 = self.cliprect.xmax
            y1 = self.cliprect.ymin - dy
            y2 = self.cliprect.ymin
            if self.angle < 0:
                y1, y2 = y2, y1
        start_line = geom.Line((x1, y1), (x2, y2))
#         if self.angle_jitter > 0:
#             # Extend the start line to provide some headroom for clipping
#             # possibly rotated line segments. This is a hack to compensate
#             # for the lack of infinite line clipping in Box...
#             # TODO: implement infinite line clipping...
#             start_line = start_line.extend(self.cliprect.diagonal(),
#                                            from_midpoint=True)
        if self.spacing_jitter > 0:
            # Compensate extent for possible spacing jitter
            max_extent += self.axis_spacing * (1 + self.spacing_jitter)
        lines = []
        offset = 0
        jitter = 0
        while offset < max_extent:
            if self.is_vertical:
                line_offset = (offset + jitter, 0)
            else:
                line_offset = (0, offset + jitter)
            line = self.angle_jittered_line(start_line + line_offset)
            segment = self.cliprect.clip_line(line)
            if segment is not None and not geom.is_zero(segment.length()):
                lines.append(segment)
            spacing = self.scaled_spacing(offset, max_extent)
            logger.debug('max_extent: %.3f, offset: %.3f, spacing: %.3f, jitter: %.3f',
                         max_extent, offset, spacing, jitter)
            offset += spacing
            if self.spacing_jitter > 0:
                jitter = spacing * self.spacing_jitter_scale()
        return lines

    def angle_jittered_line(self, line):
        """
        """
        if geom.is_zero(self.angle_jitter):
            return line
        # This produces a random angle between -pi and pi
        kappa = self.angle_jitter_kappa
        norm_angle = random.vonmisesvariate(math.pi, kappa) - math.pi
        jitter_angle = norm_angle * self.angle_jitter / math.pi
        if not geom.is_zero(jitter_angle):
            mat = transform2d.matrix_rotate(jitter_angle,
                                            origin=line.midpoint())
            line = line.transform(mat)
        return line

    def scaled_spacing(self, current_offset, max_extent):
        """
        """
        scale = 1.0
        cycle_interval = max_extent / self.varspace_cycles
        t = (current_offset % cycle_interval) / cycle_interval
        if self.spacing_formula == 'linear':
            scale = t
        elif self.spacing_formula == 'log':
            scale = math.log10(t * 9 + 1)
        elif self.spacing_formula == 'sine':
            scale = abs(math.sin(t * math.pi * 2))
        if scale < 1.0 and self.varspace_invert:
            scale = 1.0 - scale
        logger.debug('interval=%f, t=%f, scale=%f', cycle_interval, t, scale)
        spacing = self.axis_spacing * scale
        return min(max(spacing, self.varspace_min), self.varspace_max)

    def spacing_jitter_scale(self):
        """
        """
        mu = 0
        sigma = 0.4
        jitter = random.normalvariate(mu, sigma)
        return jitter * self.spacing_jitter


if __name__ == '__main__':
    Lines().main(Lines.OPTIONSPEC)
