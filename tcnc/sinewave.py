#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
Approximate a sine wave using Bezier curves and draw it as SVG.

This can be invoked as an Inkscape extension or from the command line.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division, unicode_literals)
# Uncomment this if any of these builtins are used.
# from future_builtins import (ascii, filter, hex, map, oct, zip)

import gettext

from inkscape import inkext
from geom import bezier

__version__ = '0.2'

_ = gettext.gettext


class SineWave(inkext.InkscapeExtension):
    """An Inkscape extension that draws a sine wave using Bezier curves.
    """
    # Command line options
    _OPTIONSPEC = (
        inkext.ExtOption('--amplitude', '-a', type='docunits', default=1.0,
                         help=_('Amplitude')),
        inkext.ExtOption('--wavelength', '-w', type='docunits', default=1.0,
                         help=_('Wavelength')),
        inkext.ExtOption('--cycles', '-c', type='int', default=1,
                         help=_('Number of cycles')),
        inkext.ExtOption('--origin_x', type='docunits', default=0.0,
                         help=_('Origin X')),
        inkext.ExtOption('--origin_y', type='docunits', default=0.0,
                         help=_('Origin X')),
    )

    _LAYER_NAME = 'sine wave'
    _LINE_STYLE = 'fill:none;stroke:#000000;stroke-width:1px;stroke-opacity:1;'

    def run(self):
        """Main entry point for Inkscape extensions.
        """
        # Create a new layer since there is currently no way for
        # an extension to determine the currently active layer...
        self.line_layer = self.svg.create_layer(self._LAYER_NAME,
                                                incr_suffix=True, flipy=True)
        # Approximate a sine wave using Bezier curves
        origin = (self.options.origin_x, self.options.origin_y)
        sine_path = bezier.bezier_sine_wave(self.options.amplitude,
                                            self.options.wavelength,
                                            cycles=self.options.cycles,
                                            origin=origin)
        # Draw the sine wave
        style = self.svg.scale_inline_style(self._LINE_STYLE)
        self.svg.create_polypath(sine_path, style=style, parent=self.line_layer)


if __name__ == '__main__':
    ext = SineWave()
    ext.main(SineWave._OPTIONSPEC)
