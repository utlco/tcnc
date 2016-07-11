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

import math
# import logging

import geom

from . import util
from . import simplecam

class PaintCAM(simplecam.SimpleCAM):
    """
    """

    def __init__(self, gcode, **kwargs):
        """
        :gcode: a GCode instance
        """
        super(PaintCAM, self).__init__(gcode, **kwargs)

        #: Add overshoot to path end
        self.brush_overshoot_enable = False
        #: Use tool width to determine overshoot
        #: Overrides manual overshoot distance
        self.brush_overshoot_auto = False
        #: Manual overshoot distance
        self.brush_overshoot_distance = self.tool_trail_offset
        #: Add a soft landing to lower tool during feed at start of path.
        self.brush_soft_landing = False
        #: Landing strip distance to prepend to start of path
        self.brush_landing_strip = 0.0

        #: Enable brush reload sequence
        self.brush_reload_enable = False
        #: Enable rotation to reload angle before pause.
        self.brush_reload_rotate = False
        #: Brush reload angle.
        self.brush_reload_angle = 0.0
        #: Pause/dwell brush at reload (after rotation).
        self.brush_reload_pause = False
        #: Dwell time for brush reload.
        self.brush_reload_dwell = 0.0
        #: Number of paths to process before brush reload.
        self.brush_reload_max_paths = 1

    def preprocess_paths(self, path_list):
        """Overrides SimpleCAM.preprocess_paths().
        """
        path_list = super(PaintCAM, self).preprocess_paths(path_list)

        if self.debug_svg is not None:
            brush_layer = self.debug_svg.create_layer('debug_brush', flipy=True)

        new_path_list = []
        for path in path_list:
            if self.brush_overshoot_enable or self.brush_soft_landing:
                path = self.process_brush_path(path)
            new_path_list.append(path)

        if self.debug_svg is not None:
            for path in path_list:
                geom.debug.plot_path(path, color='#ff0066', layer=brush_layer)

        return new_path_list

    def generate_rapid_move(self, path):
        """Generate G code for a rapid move to the beginning of the tool path.
        """
        if (self.brush_reload_enable and
            (self._path_count % self.brush_reload_max_paths) == 0):
            start_segment = path[0]
            if self.brush_reload_rotate:
                # Coordinated move to XY and A reload angle
                rotation = geom.calc_rotation(self.current_angle,
                                              self.brush_reload_angle)
                self.current_angle += rotation
                self.gc.rapid_move(start_segment.p1.x, start_segment.p1.y,
                                   a=self.current_angle)
            else:
                self.gc.rapid_move(start_segment.p1.x, start_segment.p1.y)
            if self.brush_reload_dwell > 0:
                self.gc.dwell(self.brush_reload_dwell * 1000)
            elif self.brush_reload_pause:
                self.gc.pause()
        super(PaintCAM, self).generate_rapid_move(path)

    def process_brush_path(self, path):
        """
        """
        start_angle = util.seg_start_angle(path[0])
        # First prepend the landing strip if any.
        strip_dist = self.brush_landing_strip
        if strip_dist > self.gc.tolerance:
            delta = geom.P.from_polar(strip_dist, start_angle + math.pi)
            segment = geom.Line(path[0].p1 + delta, path[0].p1)
            if hasattr(path[0], 'inline_start_angle'):
                segment.inline_end_angle = path[0].inline_start_angle
            path.insert(0, segment)
        # Then prepend the soft landing segment.
        landing_dist = self.tool_trail_offset
        if self.brush_soft_landing and landing_dist > self.gc.tolerance:
            delta = geom.P.from_polar(landing_dist, start_angle + math.pi)
            segment = geom.Line(path[0].p1 + delta, path[0].p1)
            if hasattr(path[0], 'inline_start_angle'):
                segment.inline_end_angle = path[0].inline_start_angle
            path.insert(0, segment)
#         d = max(self.tool_trail_offset, 0.01)
#         if first_segment.length() > d:
#             # If the segment is longer than the brush trail
#             # cut it into two segments and use the first as the landing.
#             seg1, seg2 = first_segment.subdivide(d / first_segment.length())
#             path[0] = seg1
#             path.insert(1, seg2)
        path[0].inline_z = self.z_step

        # Append overshoot segments if brush overshoot is enabled
        if self.brush_overshoot_enable:
            if self.brush_overshoot_auto:
                overshoot_dist = self.tool_width / 2
            else:
                overshoot_dist = self.brush_overshoot_distance
#             logger.debug('tw=%f, od=%f' % (self.tool_width, overshoot_dist))
            segment = path[-1]
            brush_direction = util.seg_end_angle(segment)
            if overshoot_dist > self.gc.tolerance:
                delta = geom.P.from_polar(overshoot_dist, brush_direction)
                overshoot_endp = segment.p2 + delta
                overshoot_line = geom.Line(segment.p2, overshoot_endp)
                path.append(overshoot_line)
            if self.brush_soft_landing:
                liftoff_dist = self.tool_trail_offset
                if liftoff_dist > self.gc.tolerance:
                    delta = geom.P.from_polar(liftoff_dist, brush_direction)
                    liftoff_endp = overshoot_endp + delta
                    liftoff_line = geom.Line(overshoot_endp, liftoff_endp)
                    liftoff_line.inline_z = 0.0
                    path.append(liftoff_line)
        return path
