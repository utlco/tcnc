#!/usr/bin/env python
#-----------------------------------------------------------------------------#
#    Copyright 2012-2016 Claude Zervas
#    email: claude@utlco.com
#-----------------------------------------------------------------------------#
"""Smooth non-G1 path nodes using Bezier curves and draw it as SVG.

Works for polyline/polygons made of line/arc segments.

This can be invoked as an Inkscape extension or from the command line.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division, unicode_literals)
# from future_builtins import (ascii, filter, hex, map, oct, zip)

import itertools
import random
import gettext
import logging

from lxml import etree

from geom import transform2d
from inkscape import inkext
import svg
from svg.svg import svg_ns

_ = gettext.gettext
logger = logging.getLogger(__name__)


class BreakShuffle(inkext.InkscapeExtension):
    """An Inkscape extension that smoothes polygons.
    """
    # Command line options
    OPTIONSPEC = (
        inkext.ExtOption('--shuffle', type='inkbool', default=False,
                         help=_('Shuffle between layers')),
#         inkext.ExtOption('--shuffle', default='alt',
#                          help=_('Path shuffle method')),
#         inkext.ExtOption('--shuffle-pathdir', default='',
#                          help=_('Path direction shuffle method')),
        inkext.ExtOption('--break-paths', type='inkbool', default=False,
                         help=_('Break paths')),
    )

    _LAYER_NAME = 'breakshuffle'

    def run(self):
        """Main entry point for Inkscape extensions.
        """
        if not self.options.shuffle and not self.options.break_paths:
            return

        layer_elements = []
        selected_elements = self.get_elements(selected_only=True)
        if selected_elements:
            layer_elements.append(selected_elements)
        else:
            layers = self.svg.get_visible_layers()
            for layer in layers:
                elements = self.svg.get_layer_elements(layer)
                if elements:
                    layer_elements.append(elements)

        layer_paths = []
        for elements in layer_elements:
            # Filter elements for just the path elements
            paths = [node for node in elements if node.tag == svg_ns('path')]
            logger.debug('ne=%d, np=%d', len(elements), len(paths))
            if paths:
                layer_paths.append(paths)

        if not layer_paths:
            # Nothing to do - so bail.
            # TODO: Maybe let the user know...
            return

        # Create a new layer for the SVG output.
        new_layer = self.svg.create_layer(self._LAYER_NAME, incr_suffix=True)

        if self.options.break_paths:
            broken_layer_paths = []
            for paths in layer_paths:
                broken_paths = []
                for path in paths:
                    path_data = path.get('d')
                    path_style = path.get('style')
                    path_transform = self.svg.get_element_transform(path)
                    transform_attr = None
                    if not transform2d.is_identity_transform(path_transform):
                        transform_attr = svg.svg.transform_attr(path_transform)
#                     logger.debug('transform: %s, %s', str(path_transform), transform_attr)
                    dlist = svg.svg.break_path(path_data)
                    for d in dlist:
                        attr = {'d': d}
                        if path_style is not None and path_style:
                            attr['style'] = path_style
                        if transform_attr is not None:
                            attr['transform'] = transform_attr
                        element = etree.Element(svg_ns('path'), attr)
                        broken_paths.append(element)
#                         self.svg.create_path(attr, style=path_style,
#                                              parent=new_layer)
                broken_layer_paths.append(broken_paths)
            layer_paths = broken_layer_paths

        if self.options.shuffle:
            all_paths = list(itertools.chain(*layer_paths))
            random.shuffle(all_paths)
            for path in all_paths:
                new_layer.append(path)
        else:
            # Just add the borken paths...
            for paths in layer_paths:
                for path in paths:
                    new_layer.append(path)


if __name__ == '__main__':
    BreakShuffle().main(BreakShuffle.OPTIONSPEC)
