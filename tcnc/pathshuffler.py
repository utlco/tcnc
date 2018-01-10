#!/usr/bin/env python
#-----------------------------------------------------------------------------#
#    Copyright 2012-2016 Claude Zervas
#    email: claude@utlco.com
#-----------------------------------------------------------------------------#
"""Randomly shuffle path order.

Optionally break apart (explode) paths at node points.
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
        inkext.ExtOption('--shuffle', type='inkbool', default=True,
                         help=_('Shuffle paths')),
        inkext.ExtOption('--explode-paths', type='inkbool', default=False,
                         help=_('Explode paths')),
        inkext.ExtOption('--reverse-order', type='inkbool', default=False,
                         help=_('Reverse path order')),
        inkext.ExtOption('--method', default='shuffle',
                         help=_('Path arrangement method')),
#         inkext.ExtOption('--shuffle-pathdir', default='',
#                          help=_('Path direction shuffle method')),
    )

    _LAYER_NAME = 'shuffled-paths'

    def run(self):
        """Main entry point for Inkscape extensions.
        """
        if not self.options.shuffle and not self.options.explode_paths:
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

        # Explode the paths first
        if self.options.explode_paths:
            exploded_layer_paths = []
            for paths in layer_paths:
                exploded_paths = []
                for path in paths:
                    path_data = path.get('d')
                    path_style = path.get('style')
                    path_transform = self.svg.get_element_transform(path)
                    transform_attr = None
                    if not transform2d.is_identity_transform(path_transform):
                        transform_attr = svg.svg.transform_attr(path_transform)
                    dlist = svg.svg.explode_path(path_data)
                    for d in dlist:
                        attr = {'d': d}
                        if path_style is not None and path_style:
                            attr['style'] = path_style
                        if transform_attr is not None:
                            attr['transform'] = transform_attr
                        element = etree.Element(svg_ns('path'), attr)
                        exploded_paths.append(element)
                exploded_layer_paths.append(exploded_paths)
            layer_paths = exploded_layer_paths

        all_paths = list(itertools.chain(*layer_paths))
        if self.options.method == 'shuffle':
            random.shuffle(all_paths)
#            for path in all_paths:
#                new_layer.append(path)
        elif self.options.method == 'reverse':
            all_paths.reverse()
#        else:
#            # Just add the exploded paths...
#            for paths in layer_paths:
#                for path in paths:
#                    new_layer.append(path)
        for path in all_paths:
            new_layer.append(path)


if __name__ == '__main__':
    BreakShuffle().main(BreakShuffle.OPTIONSPEC)
