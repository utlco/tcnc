#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
Python port of quasi.c which was originally written by Eric Weeks
weeks@physics.emory.edu

See: http://www.physics.emory.edu/~weeks/software/quasic.html

This algorithm implements the "Generalized Dual Method" or GDM.
See [Socolar, Steinhardt, Levine] 1985.

Mostly unchanged except to make it a little more pythonic and:
    - Removed Postscript output and main()
    - Fixed divide by zero exception for even symmetries
    - Added segment connection to vertices options
    - Removed coloring - should be done in plotter

====
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import math


class QuasiPlotter(object):
    """Quasi plotter base class.
    Subclass this to produce output.

    Does nothing by default.
    """
    def plot_polygon(self, dummy_vertices, dummy_color):
        """Draw a polygon.

        Args:
            vertices: A list of tuples containing the (x,y) coordinates of the
                polygon vertices.
            color: Fill color. A value between 0.0 and 1.0 or None if
                no fill.

        Returns:
            True if the polygon is not clipped, otherwise False.
        """
        return False

    def plot_segment(self, p1, p2):
        """Draw a line segment.

        Args:
            p1: Segment start point as tuple containing (x,y) coordinates.
            p2:  Segment end point as tuple containing (x,y) coordinates.
        """
        pass


class _QVector(object):
    """ Unit vector describing a line used to generate tiling.
    """

    def __init__(self, angle, slot, numlines, salt_x, salt_y):
        """
        Args:
            angle: The vector angle
            slot: The integer polar index of the angle.
                A number >= 0 and < (symmetry).
            numlines: The number of offset lines
            salt_x: A random-ish value used to avoid line intersections
                of more than two.
            salt_y: A random-ish value used to avoid line intersections
                of more than two.
        """
        self.x = math.cos(angle)
        self.y = math.sin(angle)
        self.m = self.y / self.x
        # Calculate the Y intercepts of the parallel offset lines
        self.b = []
        for r in range(numlines):
            y1 = (self.y * (slot * salt_y)) - (self.x * (r - numlines/2))
            x1 = (self.x * (slot * salt_x)) + (self.y * (r - numlines/2))
            self.b.append(y1 - (self.m * x1))


class Quasi(object):
    # Segment connection types
    SEG_NONE = 0
    """No segment connection."""
    SEG_MIDP_ACUTE = 1
    """Connect midpoints of polygon edges that meet at an acute angle."""
    SEG_MIDP_OBTUSE = 2
    """Connect midpoints of polygon edges that meet at an obtuse angle."""
    SEG_MIDP_CROSS = 3
    """Connect midpoints of polygon edges to form a cross."""
    SEG_MIDP_RECT = 4
    """Connect midpoints of polygon edges to form a rectangle."""
    SEG_VERT_ACUTE = 5
    """Connect polygon vertices whose edges form an acute angle."""
    SEG_VERT_OBTUSE = 6
    """Connect polygon vertices whose edges form an obtuse angle."""
    SEG_VERT_CROSS = 7
    """Connect polygon vertices to form a cross."""

    _RAD_INCR = 0.4 #3 #0.4

    def _segtype_midp(self, segtype):
        return 0 < segtype < 5

    def __init__(self, symmetry=5, segtype_skinny=SEG_NONE,
                 segtype_fat=SEG_NONE, plotter=None, tolerance=1e-08):
        """
        Args:
            symmetry: Degrees of symmetry. Must be at least two.
            segtype_skinny: Segment connection type for skinny rhombuses.
                Default is SEG_NONE.
            segtype_fat: Segment connection type for fat rhombuses.
                Default is SEG_NONE.
            plotter: Plotter to draw output. Default is None.
            tolerance: Tolerance for floating point comparisons.
                Default is 1e-08.
        """
        #: Tolerance for floating point comparisons
        self.tolerance = tolerance
        self._precision = max(0, int(round(abs(math.log(tolerance, 10)))))
        #: Plotter to draw output.
        self.plotter = plotter
        if plotter is None:
            self.plotter = QuasiPlotter()
        #: Degrees of quasi symmetry.
        self.symmetry = symmetry
        self.segtype_skinny = segtype_skinny
        self.segtype_fat = segtype_fat
        #: Split crossed segments
        self.segment_split_cross = False
        #: Random-ish offset to avoid more than two lines intersecting.
        self.offset_salt_x = 0.2137#0.314159
        #: Random-ish offset to avoid more than two lines intersecting.
        self.offset_salt_y = 0.1132#0.1618
        #: Ratio that determines segment edge midpoint.
        self.segment_ratio = 0.5
        """Ratio that determines edge midpoint."""
        #: Ratio that determines whether a rhombus is fat or skinny
        self.skinnyfat_ratio = 0.2
        #: Number of lines. A larger number enables more tiles to be generated.
        self.numlines = 30
        #: Color fill polygons. Default is False.
        self.color_fill = False
        #: Fill color by rhombus type.
        self.color_by_polytype = False

    def quasi(self):
        """Draw tiling.
        """
        index = [0,] * self.symmetry
        maxline = self.numlines - 1
        minline = maxline / 2
        minrad = 0.0
        vectors = self._init_vectors()

        while minrad <= float(maxline):
            rad1 = minrad * minrad
            minrad += self._RAD_INCR
            rad2 = minrad * minrad
            for n in range(1, maxline):
                n2 = (n - minline) * (n - minline)
                for m in range(1, maxline):
                    rad = float(n2 + (m - minline) * (m - minline))
                    if rad1 <= rad < rad2:
                        # v1 is 1st direction, v2 is 2nd.
                        # Look for intersection between pairs
                        # of lines in these two directions. (will be x0,y0)
                        for t in range(self.symmetry - 1):
                            for r in range(t + 1, self.symmetry):
                                v1 = vectors[t]
                                v2 = vectors[r]
                                x0 = (v1.b[n] - v2.b[m]) / (v2.m - v1.m)
                                y0 = v1.m*x0 + v1.b[n]
                                do_plot = True
                                for i in range(self.symmetry):
                                    if i != t and i != r:
                                        v = vectors[i]
                                        dx = -x0*v.y + (y0 - v.b[0])*v.x
                                        index[i] = int(-dx)
                                        if (index[i] > self.numlines - 3
                                                or index[i] < 1):
                                            do_plot = False
                                            break
                                if do_plot:
                                    index[t] = n - 1
                                    index[r] = m - 1
                                    self._plot(vectors, v1, v2, index)

    def _init_vectors(self):
        """Initialize and construct vectors for a de Bruijn grid.
        """
        vectors = []
        phi = 2*math.pi / self.symmetry
        # Even symmetries will produce line slopes of zero
        # which will cause a divide by zero exception.
        # In such cases the vector angles are slightly rotated.
        if self.symmetry % 2 == 0:
            angle = self.tolerance * 10
        else:
            angle = 0.0
        for t in range(self.symmetry):
            v = _QVector(angle, t, self.numlines,
                         self.offset_salt_x, self.offset_salt_y)
            vectors.append(v)
            angle += phi
        return vectors

    def _plot(self, vectors, v1, v2, index):
        x0 = 0.0
        y0 = 0.0
        for i in range(self.symmetry):
            x0 += vectors[i].x * index[i]
            y0 += vectors[i].y * index[i]
        vertices = ((x0, y0),
                    (x0 + v1.x, y0 + v1.y),
                    (x0 + v1.x + v2.x, y0 + v1.y + v2.y),
                    (x0 + v2.x, y0 + v2.y))
        # The dot product of the two vectors.
        # A measure of how 'skinny' the rhombus is.
        dotp = v1.x * v2.x + v1.y * v2.y
        if not self.plotter.plot_polygon(vertices, self._round(abs(dotp))):
            return
        if self.segtype_skinny > 0 or self.segtype_fat > 0:
            # Determine if the polygon is fat or skinny
            is_skinny = abs(dotp) > self.skinnyfat_ratio
            segtype = self.segtype_skinny if is_skinny else self.segtype_fat
            if self._segtype_midp(segtype):
                # Calculate segment endpoints
                x1 = v1.x * self.segment_ratio
                y1 = v1.y * self.segment_ratio
                x2 = v2.x * self.segment_ratio
                y2 = v2.y * self.segment_ratio
                if dotp > 0:
                    # Swap the acute/obtuse vertices
                    segpoly = ((x0 + v1.x + x2, y0 + v1.y + y2),
                               (x0 + v2.x + x1, y0 + v2.y + y1),
                               (x0 + x2, y0 + y2), (x0 + x1, y0 + y1))
                else:
                    segpoly = ((x0 + x1, y0 + y1),
                               (x0 + v1.x + x2, y0 + v1.y + y2),
                               (x0 + v2.x + x1, y0 + v2.y + y1),
                               (x0 + x2, y0 + y2))
                if segtype == Quasi.SEG_MIDP_ACUTE:
                    self.plotter.plot_segment(segpoly[0], segpoly[1])
                    self.plotter.plot_segment(segpoly[2], segpoly[3])
                elif segtype == Quasi.SEG_MIDP_OBTUSE:
                    self.plotter.plot_segment(segpoly[0], segpoly[3])
                    self.plotter.plot_segment(segpoly[1], segpoly[2])
                elif segtype == Quasi.SEG_MIDP_CROSS:
                    if self.segment_split_cross and self.segment_ratio == 0.5:
                        mid_x = (segpoly[0][0] + segpoly[2][0]) * 0.5
                        mid_y = (segpoly[0][1] + segpoly[2][1]) * 0.5
                        midp = (mid_x, mid_y)
                        self.plotter.plot_segment(segpoly[0], midp)
                        self.plotter.plot_segment(midp, segpoly[2])
                        self.plotter.plot_segment(segpoly[1], midp)
                        self.plotter.plot_segment(midp, segpoly[3])
                    else:
                        self.plotter.plot_segment(segpoly[0], segpoly[2])
                        self.plotter.plot_segment(segpoly[1], segpoly[3])
                elif segtype == Quasi.SEG_MIDP_RECT:
                    self.plotter.plot_segment(segpoly[0], segpoly[1])
                    self.plotter.plot_segment(segpoly[2], segpoly[3])
                    self.plotter.plot_segment(segpoly[0], segpoly[3])
                    self.plotter.plot_segment(segpoly[1], segpoly[2])
            else:
                if segtype == Quasi.SEG_VERT_ACUTE:
                    self.plotter.plot_segment(vertices[1], vertices[3])
                elif segtype == Quasi.SEG_VERT_OBTUSE:
                    self.plotter.plot_segment(vertices[0], vertices[2])
                elif segtype == Quasi.SEG_VERT_CROSS:
                    if self.segment_split_cross:
                        mid_x = (vertices[0][0] + vertices[2][0]) * 0.5
                        mid_y = (vertices[0][1] + vertices[2][1]) * 0.5
                        midp = (mid_x, mid_y)
                        self.plotter.plot_segment(vertices[0], midp)
                        self.plotter.plot_segment(midp, vertices[2])
                        self.plotter.plot_segment(vertices[1], midp)
                        self.plotter.plot_segment(midp, vertices[3])
                    else:
                        self.plotter.plot_segment(vertices[0], vertices[2])
                        self.plotter.plot_segment(vertices[1], vertices[3])

    def _round(self, n):
        """Round a floating point number to the current PRECISION."""
        return round(n, self._precision)

    def _float_eq(self, a, b):
        """Compare two floats for equality."""
        return abs(a - b) < self.tolerance


