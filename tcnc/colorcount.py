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

import geom.debug
from geom import polygon
from svg import css
from svg import geomsvg
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
        inkext.ExtOption('--key-font-size', type='string', default='12pt',
                         help=_('Key font size')),
        inkext.ExtOption('--use-shape-key', type='inkbool', default=True,
                         help=_('Use first shape as key')),
        inkext.ExtOption('--tag-shapes', type='inkbool', default=True,
                         help=_('Annotate filled shapes')),
        inkext.ExtOption('--tag-font-size', type='string', default='9pt',
                         help=_('Annotation font size')),
        inkext.ExtOption('--tag-prefix', type='string', default='C',
                         help=_('Annotation prefix')),
        inkext.ExtOption('--tag-enum-start', type='int', default=1,
                         help=_('Enumeration start')),
    )

    _styles = {
        'keytext':
            'font-family:Arial;'
            'font-size:$key_font_size;'
            'fill:#000000;stroke:none;',
        'tagtext':
            'font-family:Arial;'
            'font-size:$tag_font_size;'
            'fill:#000000;stroke:none;',
        'colorbox':
            'fill:%s;stroke:#606060;stroke-width:$colorbox_stroke_width',
        'keyshape':
            'fill:none;stroke:#000000;stroke-width:$shapekey_stroke_width;',
    }

    _style_defaults = {
        'key_font_size': '12pt',
        'tag_font_size': '9pt',
        'colorbox_stroke_width': '1pt',
        'shapekey_stroke_width': '1pt',
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

        pathlist = []
        self.color_layers = {}
        color_count = {}
        color_shape = {}
        svg_elements = self.svg.get_shape_elements(self.get_elements())
        if svg_elements:
            for element, element_transform in svg_elements:
                style = element.get('style')
                if style is not None:
                    stylemap = css.inline_style_to_dict(style)
                    fill_color = stylemap.get('fill')
                    if fill_color is not None:
                        paths = geomsvg.svg_element_to_geometry(
                            element, element_transform)
                        for path in paths:
                            pathlist.append((path, fill_color))
                        if fill_color in color_count:
                            color_count[fill_color] += 1
                        else:
                            color_count[fill_color] = 1
                            color_shape[fill_color] = paths[0]
                            if self.options.separate_layers:
                                self._add_color_layer(element, fill_color)
                        if self.options.separate_layers:
                            self._copy_to_layer(element, fill_color)

        if color_count:
            self.key_font_height = self.svg.unit2uu(self.options.key_font_size)
            self.key_line_height = self.key_font_height * 1.5
            self.key_bottom_margin = self.key_font_height * 1.5
            self.key_left_margin = self.svg.unit2uu('10px')
            self.key_top_margin = self.svg.unit2uu('30px')
            self.key_layer = self.svg.create_layer('colorkey')
            if self.options.tag_shapes:
                self.tag_layer = self.svg.create_layer('colortags')
            if self.options.use_shape_key:
                self._draw_color_key_shapes(color_count, color_shape)
            else:
                self._draw_color_key_boxes(color_count)
            if self.options.tag_shapes:
                self._tag_shapes(pathlist, color_count)
                
    def _draw_color_key_shapes(self, color_count, color_shape):
        total_count = 0
        line_y = self.key_top_margin
        colors = color_count.keys()
        for color in colors:
            count = color_count[color]
            path = color_shape[color]
            bbox = self._path_bbox(path)
            color_index = colors.index(color)
            self._draw_key_shape(path, bbox, line_y, color_index)
            line_y += bbox.height() + self.key_line_height
            self._draw_key_item_text(line_y, count, color)
            line_y += self.key_bottom_margin
            total_count += count
        self._draw_key_total(line_y + self.key_line_height, total_count)
  
    def _draw_color_key_boxes(self, color_count):
        total_count = 0
        colorbox_width = self.svg.unit2uu(self._COLORBOX_WIDTH)
        colorbox_height = self.svg.unit2uu(self._COLORBOX_HEIGHT)
        line_y = self.key_top_margin
        for color, count in color_count.items():
            colorbox_style = self._styles['colorbox'] % color
            self.svg.create_rect((self.key_left_margin, line_y),
                                 colorbox_width, colorbox_height,
                                 style=colorbox_style,
                                 parent=self.key_layer)
            line_y += colorbox_height + self.key_line_height
            self._draw_key_item_text(line_y, count, color)
            line_y += self.key_bottom_margin
            total_count += count
        self._draw_key_total(line_y + self.key_line_height, total_count)

    def _draw_key_shape(self, path, bbox, line_y, color_index):
        poly = self._path_to_poly(path)
        # Translate the polygon to the key location
        dx = self.key_left_margin - bbox.p1.x
        dy = line_y - bbox.p1.y
        tpoly = []
        for p in poly:
            tp = p + (dx, dy)
            tpoly.append(tp)
        self._draw_annotation(polygon.centroid(tpoly), color_index,
                              self.key_layer)
        self.svg.create_polygon(tpoly, style=self._styles['keyshape'],
                                parent=self.key_layer)
        
    def _draw_key_item_text(self, line_y, count, color):
        text = 'count: %d, color: %s' % (count, color)
        self.svg.create_text(text, self.key_left_margin, line_y,
                             style=self._styles['keytext'],
                             parent=self.key_layer)
        
    def _draw_key_total(self, line_y, total_count):
        text = 'Total: %d' % total_count
        self.svg.create_text(text, self.key_left_margin, line_y,
                             style=self._styles['keytext'],
                             parent=self.key_layer)
        
    def _tag_shapes(self, pathlist, color_count):
        """
        """
        colors = color_count.keys()
        for path, fill_color in pathlist:
            color_index = colors.index(fill_color)
            self._draw_annotation(self._path_centroid(path), color_index,
                                  self.tag_layer)

    def _draw_annotation(self, centroid, color_index, layer):
        tag_suffix = '{:d}'.format(color_index + self.options.tag_enum_start)
        tag = self.options.tag_prefix + tag_suffix
        offset = self.svg.unit2uu(self.options.tag_font_size) / 2
        text_pos = centroid + (-offset, offset)
        self.svg.create_text(tag, text_pos.x, text_pos.y,
                             style=self._styles['tagtext'],
                             parent=layer)
                 
    def _path_centroid(self, path):
        # For now pretend each path element is a straight line segment
        # and convert the path into a polygon to determine centroid...
        poly = self._path_to_poly(path)
        return polygon.centroid(poly)

    def _path_bbox(self, path):
        poly = self._path_to_poly(path)
        return polygon.bounding_box(poly)
  
    def _path_to_poly(self, path):
        """
        Naive conversion of a path to a polygon
        """
        poly = [path[0].p1]
        for shape in path:
            poly.append(shape.p2)
        return poly
        
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
