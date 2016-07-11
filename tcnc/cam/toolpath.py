#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import geom


class ToolpathException(Exception):
    """"""
    pass

class Toolpath(list):
    """A Toolpath is an ordered list of Line and Arc segments.
    """

    def __init__(self):
        """
        """

    def biarc_approximation(self, path, tolerance, max_depth, line_flatness):
        """Append the path while converting all cubic bezier curves
        to biarcs (tangentially connected circular arcs).

        Args:
            path: An iterable collection of
                bezier.CubicBezier, geom.Line, or geom.Arc objects.
            tolerance: Approximation tolerance. A lower value increases
                accuracy at the cost of time and number of generated
                biarc segments.
            max_depth: Maximum recursion depth. This limits how many times
                the Bezier curve can be subdivided.
            line_flatness: Segments flatter than this value will be converted
                to straight line segments instead of arcs with huge radii.
                Generally this should be a small value (say <= 0.01) to avoid
                path distortions.

        Raises:
            ToolpathException: If the path contains anything other
            than CubicBezier, Line, or Arc segments.
        """
        for segment in path:
            if isinstance(segment, geom.bezier.CubicBezier):
                biarcs = segment.biarc_approximation(tolerance=tolerance,
                                                    max_depth=max_depth,
                                                    line_flatness=line_flatness)
                self.extend(biarcs)
            elif (isinstance(segment, geom.Line) or
                  isinstance(segment, geom.Arc)):
                self.append(segment)
            else:
                raise ToolpathException('Invalid path segment type: %s' %
                                        segment.__name__)

    def verify_continuity(self):
        """Verify that this path has point continuity (C0/G0).
        """
        prev_seg = self[0]
        for segment in self[1:]:
            if prev_seg.p2 != segment.p1:
                return False
            prev_seg = segment
        return True

    def is_closed(self):
        """Return True if this path forms a closed polygon."""
        return len(self) > 2 and self[0].p1 == self[-1].p2

