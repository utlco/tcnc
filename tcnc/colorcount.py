#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
An Inkscape extension to count the number of unique SVG fill colors.

====
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division, unicode_literals)
# Uncomment this if any of these builtins are used.
# from future_builtins import (ascii, filter, hex, map, oct, zip)

import gettext
# import logging

from copy import deepcopy

import geom

from svg import css
from inkscape import inkext

__version__ = "0.1"

_ = gettext.gettext
# logger = logging.getLogger(__name__)


class ColorCount(inkext.InkscapeExtension):
    """Inkscape plugin that traces paths on edge connected graphs.
    """
    OPTIONSPEC = (
        inkext.ExtOption('--separate-layers', type='inkbool', default=True,
                         help=_('Copy colored elements to separate layers')),
    )

    _styles = {
        'text':
            'font-family:Sans;'
            'font-size:$font_size;line-height:125%;'
            'fill:#000000;stroke:none;',
        'colorbox':
            'fill:%s;stroke:#606060;stroke-width:$colorbox_stroke_width'
    }

    _style_defaults = {
        'font_size': '12pt',
        'colorbox_stroke_width': '1pt',
    }

    _COLORBOX_HEIGHT = '.5in'
    _COLORBOX_WIDTH = '1in'

    def run(self):
        """Main entry point for Inkscape extension.
        """
        geom.debug.set_svg_context(self.debug_svg)

        styles = self.svg.styles_from_templates(self._styles,
                                                self._style_defaults,
                                                self.options.__dict__)
        self._styles.update(styles)

        self.color_layers = {}
        color_count = {}
        svg_elements = self.svg.get_shape_elements(self.get_elements())
        if svg_elements:
            for element, unused_element_transform in svg_elements:
                style = element.get('style')
                if style is not None:
                    stylemap = css.inline_style_to_dict(style)
                    fill_color = stylemap.get('fill')
                    if fill_color is not None:
                        if fill_color in color_count:
                            color_count[fill_color] += 1
                        else:
                            color_count[fill_color] = 1
                            if self.options.separate_layers:
                                self._add_color_layer(element, fill_color)
                        if self.options.separate_layers:
                            self._copy_to_layer(element, fill_color)

        if color_count:
            count_layer = self.svg.create_layer('colorcount')
            text = []
            total_count = 0
            colorbox_width = self.svg.unit2uu(self._COLORBOX_WIDTH)
            colorbox_height = self.svg.unit2uu(self._COLORBOX_HEIGHT)
            line_height = self.svg.unit2uu('16pt')
            pp_height = colorbox_height + line_height + self.svg.unit2uu('12pt')
            left_margin = self.svg.unit2uu('10px')
            next_line_y = self.svg.unit2uu('30px')
            for color, count in color_count.items():
                colorbox_style = self._styles['colorbox'] % color
                self.svg.create_rect((left_margin, next_line_y),
                                     colorbox_width, colorbox_height,
                                     style=colorbox_style,
                                     parent=count_layer)
                text = '%s: %d' % (color, count)
                self.svg.create_text(text, left_margin,
                                     next_line_y + colorbox_height + line_height,
                                     style=self._styles['text'],
                                     parent=count_layer)
                next_line_y += pp_height
                total_count += count
            text = 'Total: %d' % total_count
            self.svg.create_text(text,  left_margin, next_line_y + line_height,
                                 style=self._styles['text'],
                                 parent=count_layer)

    def _copy_to_layer(self, element, fill_color):
        layer = self._get_color_layer(fill_color)
        if layer is None:
            layer = self._add_color_layer(element, fill_color)
        element_copy = deepcopy(element)
        layer.append(element_copy)
#         old_parent = element.getparent()
#         old_parent.remove(element)
#         layer.append(element)


    def _add_color_layer(self, element, fill_color):
        parent_layer = self.svg.get_parent_layer(element)
        parent_name = self.svg.get_layer_name(parent_layer)
        parent_style = parent_layer.get('style')
        parent_transform = parent_layer.get('transform')
        layer_name = '%s_%s' % (parent_name, fill_color.lstrip('#'))
        color_layer = self.svg.create_layer(layer_name)
        if parent_style is not None:
            color_layer.set('style', parent_style)
        if parent_transform is not None:
            color_layer.set('transform', parent_transform)
        self.color_layers[fill_color] = color_layer
        return color_layer

    def _get_color_layer(self, fill_color):
        return self.color_layers.get(fill_color)

if __name__ == '__main__':
    ColorCount().main(optionspec=ColorCount.OPTIONSPEC)
