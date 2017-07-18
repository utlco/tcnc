#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
Simple G code generation from basic 2D geometry.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import math
import logging

import geom

from . import util
from . import fillet
from . import offset


class CAMException(Exception):
    """"""

class SimpleCAM(object):
    """Simple 2D CAM library that converts line/arc path geometry into G code
    suitable for a straightforward 2.5 axis machine with an optional
    fourth angular axis (A) that rotates about the Z axis. The fourth axis
    position is always tangential to the movement along the X and Y axes.
    This is usually called a tangential tool (ie a knife or a brush).

    Since the path geometry is two dimensional the Z and A axes are
    calculated automatically.
    By default the Z axis value is determined by the current plunge depth
    and the A axis value is the tangent normal of the current segment.

    These defaults can be overridden by assigning extra attributes
    to the segment.

    Segment attributes:

        * `inline_end_z`: The Z axis value at the end of the segment.
        * `inline_start_a`: The A axis value at the start of the segment.
        * `inline_end_a`: The A axis value at the start of the segment.
        * `inline_ignore_a`: Boolean. True if the A axis is not to be
           rotated for the length of the segment.

    """

#     _DEFAULT_INLINE_DELTAS = {'X': 0.0, 'Y': 0.0, 'Z': 0.0, 'A': 0.0}
#     _DEFAULT_INLINE_OFFSETS = {'X': 0.0, 'Y': 0.0, 'Z': 0.0, 'A': 0.0}

    def __init__(self, gcode_gen):
        """
        Args:
            gcode_gen: a :mod:`cam.gcode.GCodeGenerator` instance
        """
        self.gc = gcode_gen

        # SVG context for debug output.
        self.debug_svg = None

        # Properties will be set by user.
        # Only default initialization should be done here.

        # : Home the XYA axes when all done
        self.home_when_done = False
        # : Sort strategy
        self.path_sort_method = None
        # : Maximum feed depth per pass
        self.z_step = 0.0
        # : Final feed depth
        self.z_depth = 0.0
        # : Tangential tool width in machine units
        self.tool_width = 0.0
        # : Tool trail offset in machine units
        self.tool_trail_offset = 0.0
        # : Feed distance to travel (in machine units) before outputting
        # application-specific G code.
        # Default is 0, meaning no action.
#         self.feed_interval = 0.0
        # : Biarc approximation tolerance
        self.biarc_tolerance = 0.01
        # : Maximum bezier curve subdivision recursion for biarcs
        self.biarc_max_depth = 4
        # : Flatness of curve to convert to line
        self.line_flatness = 0.001
        # : Ignore path segment start tangent angle when rotating about A
#         self.ignore_segment_angle = False
        # : Allow tool reversal at sharp corners
        self.allow_tool_reversal = False
        # : Enable tangent rotation. Default is True.
        self.enable_tangent = True
        # : Fillet paths to compensate for tool width
        self.path_tool_fillet = False
        # : Offset paths to compensate for tool trail offset
        self.path_tool_offset = False
        # : Preserve G1 continuity for offset arcs
        self.path_preserve_g1 = False
        # : Split cam at points that are not G1 or C1 continuous
        self.path_split_cusps = False
        # : Close polygons with tool fillet
        self.path_close_polygons = False
        # : Fillet paths to smooth tool travel
        self.path_smooth_fillet = False
        # : Smoothing fillet radius
        self.path_smooth_radius = 0.01
        # : Number of paths to skip over before processing
        self.skip_path_count = 0
        # : Start outputting G code when path count reaches this
        # Useful if the job has to be stopped and restarted later.
        self.path_count_start = 1

        # Cumulative tool feed distance
        self.feed_distance = 0.0
        # Current angle of A axis
        # TODO: get rid of this and use GCode.A property
        self.current_angle = 0.0
        # Feed travel since last interval
#         self.feed_interval_travel = 0.0
        # Tiny movement accumulator
        self._tinyseg_accumulation = 0.0
        # Keep track of tool flip state
        self._tool_flip_toggle = -1

    def generate_gcode(self, path_list):
        """Generate G code from tool paths.

        :param path_list: A list of drawing paths.
            Where a drawing path is a sequential collection of
            bezier.CubicBezier, geom.Line, or geom.Arc segments.
            Other shape types will be silently ignored...
        """
        # TODO: range check various properties
        if geom.is_zero(self.z_step):
            self.z_step = self.z_depth
        # Sort paths to optimize rapid moves
        if self.path_sort_method is not None:
            path_list = self.sort_paths(path_list, self.path_sort_method)
        # Pre-process paths
        path_list = self.preprocess_paths(path_list)
        # G code header - mostly boilerplate plus some info.
        self.generate_header(path_list)
        # Make sure the tool at the safe height
        self.gc.tool_up()
        # Generate G code from paths. If the Z step is less than
        # the final tool depth then do several passes until final
        # depth is reached.
        # If the final tool depth is > 0 then just ignore the step
        # value since the tool won't reach the work surface anyway.
        if self.z_depth > 0 or self.z_step < self.z_depth:
            tool_depth = self.z_depth
        else:
            tool_depth = self.z_step
        depth_pass = 1
        while tool_depth >= self.z_depth:
            for path_count, path in enumerate(path_list, 1):
                if not path:
                    # Skip empty paths...
                    logging.getLogger(__name__).debug('Empty path...')
                    continue
                if path_count >= self.path_count_start:
                    self.gc.comment()
                    self.gc.comment('Path: %d, pass: %d, depth: %g%s' %
                                    (path_count, depth_pass,
                                     tool_depth * self.gc.unit_scale,
                                     self.gc.gc_unit))
                    # Rapidly move to the beginning of the tool path
                    self.generate_rapid_move(path)
                    # Plunge the tool to current cutting depth
                    self.plunge(tool_depth, path)
                    # Create G-code for each segment of the path
                    self.gc.comment('Start tool path')
                    for segment in path:
                        self.generate_segment_gcode(segment, tool_depth)
                    # Bring the tool back up to the safe height
#                     self.retract(tool_depth, path)
#                     # Do a fast unwind if angle is > 360deg.
#                     # Useful if the A axis gets wound up after spirals.
#                     if abs(self.current_angle) > (math.pi * 2):
#                         self.gc.rehome_rotational_axis()
#                         self.current_angle = 0.0
            # remaining z distance
            rdist = abs(self.z_depth - tool_depth)
            if rdist > self.gc.tolerance and rdist < self.z_step:
                tool_depth = self.z_depth
            else:
                tool_depth += self.z_step
            depth_pass += 1
        self.gc.tool_up()
        # Do a rapid move back to the home position if specified
        if self.home_when_done:
            self.gc.rapid_move(x=0, y=0, a=0)
        # G code footer boilerplate
        self.gc.footer()

    def preprocess_paths(self, path_list):
        """Preprocess paths.
        Sort order will be maintained.

        Args:
            path_list: A list of drawing paths.
                Where a drawing path is a sequential collection of
                bezier.CubicBezier, geom.Line, or geom.Arc objects.

        Returns:
            A new list of tool paths.
        """
#         if self.debug_svg is not None:
#             biarc_layer = self.debug_svg.create_layer('debug_biarcs',
#                                                       flipy=True)
#             if self.path_tool_fillet and self.tool_width > 0:
#                 fillet_layer = self.debug_svg.create_layer('debug_fillets',
#                                                            flipy=True)
#             if self.path_tool_offset and self.tool_trail_offset > 0:
#                 offset_layer = self.debug_svg.create_layer('debug_offsets',
#                                                            flipy=True)
#                 if self.path_preserve_g1:
#                     smooth_offset_layer = self.debug_svg.create_layer(
#                         'debug_smooth_offsets', flipy=True)
#             if self.path_smooth_fillet and self.path_smooth_radius > 0.0:
#                 smooth_layer = self.debug_svg.create_layer('debug_smooth',
#                                                            flipy=True)

#         #DEBUG
#         for path in path_list:
#             prev_seg = path[0]
#             for seg in path[1:]:
#                 if not geom.segments_are_g1(prev_seg, seg):
#                     geom.debug.draw_point(prev_seg.p2, color='#00ffff')
#                 prev_seg = seg
#             if (path[-1].p2 == path[0].p1
#                     and not geom.segments_are_g1(path[-1], path[0])):
#                 geom.debug.draw_point(path[-1].p2, color='#00ffff')
#         #DEBUG
#         if self.path_tool_offset and self.tool_trail_offset > 0:
#             for path in path_list:
#                 new_path = cam.offset_path(path, self.tool_trail_offset,
#                                             preserve_g1=self.path_preserve_g1)
#                 new_path_list.append(new_path)
#                 if self.debug_svg is not None:
#                     logger.debug('pre offset layer')
#                     geom.debug.plot_path(new_path, '#cc3333', offset_layer)

        # Process the path in several passes.
        # This could use a lot of memory but it keeps things much cleaner
        # and logically consistent.

        # First pass is converting Bezier curves to circular arcs
        # using biarc approximation then adding corner fillets for
        # tool width turn compensation. Paths will also be split
        # at non-G1 vertices if required.
        biarc_path_list = []
        for path in path_list:
            # Convert Bezier curves to circular arcs.
            path = self.path_biarc_approximation(path)
#             if self.debug_svg is not None:
#                 geom.debug.plot_path(path, '#33cc33', biarc_layer)
            # First, create fillets to compensate for tool width
            if self.path_tool_fillet and self.tool_width > 0:
                path = fillet.fillet_path(path, self.tool_width / 2,
                                        fillet_close=self.path_close_polygons,
                                        mark_fillet=True)
#                 if self.debug_svg is not None:
#                     geom.debug.plot_path(path, '#3333cc', fillet_layer)
            # Split path at cusps. This may add more than one path.
            if self.path_split_cusps:
                paths = util.split_path_g1(path)
                biarc_path_list.extend(paths)
            else:
                biarc_path_list.append(path)
        path_list = biarc_path_list

        # These passes need to be done after cusps are split since
        # the path list may have been extended.

        # Offset tool paths to compensate for tool trail
        if self.path_tool_offset and self.tool_trail_offset > 0:
            new_path_list = []
            for path in path_list:
                path = offset.offset_path(path, self.tool_trail_offset,
                                          self.line_flatness)
#                 if self.debug_svg is not None:
#                     geom.debug.plot_path(path, '#cc3333', offset_layer)
                new_path_list.append(path)
            path_list = new_path_list
            # Rebuild paths to fix broken G1 continuity caused by
            # path offsetting.
            if self.path_preserve_g1:
                new_path_list = []
                for path in path_list:
                    path = offset.fix_G1_path(path,
                                                self.biarc_tolerance,
                                                self.line_flatness)
#                     if self.debug_svg is not None:
#                         geom.debug.plot_path(path, '#cc3333', smooth_offset_layer)
                    new_path_list.append(path)
                path_list = new_path_list

        # Then, create path smoothing fillets for remaining non-G1 vertices.
        if self.path_smooth_fillet and self.path_smooth_radius > 0.0:
            new_path_list = []
            for path in path_list:
                path = fillet.fillet_path(path, self.path_smooth_radius,
                                          fillet_close=self.path_close_polygons,
                                          adjust_rotation=True)
#                 if self.debug_svg is not None:
#                     geom.debug.plot_path(path, '#ff0000', smooth_layer)
                new_path_list.append(path)
            path_list = new_path_list

        # DEBUG
#         logger.debug('a1=%f, a2=%f, a3=%f, a4=%f' % (cam.seg_start_angle(path[0]),
#                                               cam.seg_end_angle(path[0]),
#                                               cam.seg_start_angle(path[-1]),
#                                               cam.seg_end_angle(path[-1])))
#         for path in path_list:
#             prev_seg = path[0]
#             for seg in path[1:]:
#                 if not util.segments_are_g1(prev_seg, seg):
#                     prev_seg.svg_plot(color='#00ffff')
#                 prev_seg = seg
#             if not util.segments_are_g1(prev_seg, seg):
#                 seg.svg_plot(color='#00ffff')
        # DEBUG
        return path_list

    def path_biarc_approximation(self, path):
        """Convert all cubic bezier curves in the drawing path
        to biarcs (tangentially connected circular arcs).

        Args:
            path: A drawing path; an iterable collection of
            bezier.CubicBezier, geom.Line, or geom.Arc objects.

        Returns:
            A new drawing path containing only geom.Line and
            geom.Arc objects.

        Raises:
            CAMException: If the path contains anything other
                than CubicBezier, Line, or Arc segments.
        """
        new_path = []
        for segment in path:
            if isinstance(segment, geom.bezier.CubicBezier):
#                 geom.debug.draw_bezier(segment, verbose=True)
                biarcs = segment.biarc_approximation(
                                    tolerance=self.biarc_tolerance,
                                    max_depth=self.biarc_max_depth,
                                    line_flatness=self.line_flatness)
                new_path.extend(biarcs)
            elif (isinstance(segment, geom.Line)
                  or isinstance(segment, geom.Arc)):
                new_path.append(segment)
            else:
                raise CAMException('Invalid path segment type: %s'
                                              % segment.__name__)
        return new_path

    def generate_header(self, path_list):
        """Output header boilerplate and comments.
        """
        self.gc.add_header_comment((
            '',
            'Path count: %d' % len(path_list)),)
        self.gc.header()

    def plunge(self, depth, path):
        """Bring the tool down to the current working depth.

        This can be subclassed to generate custom plunge profiles.
        """
        # When the first segment has an inline Z axis hint
        # it means that there is a soft landing, in which case
        # the tool is just brought to the work surface.
        if hasattr(path[0], 'inline_z'):
            depth = 0.0
        # Bring the tool down to the plunge depth.
        self.gc.tool_down(depth)

#     def retract(self, depth, path):
#         """Lift the tool from the current working depth.
#
#         This can be subclassed to generate custom retraction profiles.
#         """
#         # If the last segment has an inline Z axis hint then the
#         # Z axis movement will be determined by that segment.
#         if not hasattr(path[-1], 'inline_z'):
#             self.gc.feed(z=0.0)
#         # Lift the tool up to safe height.
#         self.gc.tool_up()

    def generate_rapid_move(self, path):
        """Generate G code for a rapid move to the beginning of the tool path.
        """
        # TODO: Unwind large rotations
        first_segment = path[0]
        segment_start_angle = util.seg_start_angle(first_segment)
        if self.enable_tangent:
            rotation = geom.calc_rotation(self.current_angle, segment_start_angle)
            self.current_angle += rotation
        self.gc.rapid_move(first_segment.p1.x, first_segment.p1.y,
                           a=self.current_angle)

    def sort_paths(self, path_list, sort_method='optimize'):
        """Sort the tool paths to minimize tool movements.
        This will try to sort the tool paths to minimize tool travel
        between the end of one path and the start of the next path.

        Args:
            path_list: A list of tool paths.
            sort_method: Sorting strategy.

        Returns:
            A sorted list of paths.
        """
        if sort_method == 'flip':
            # Preserve original path order but flip path directions to
            # minimize rapid travel.
            self._flip_paths(path_list)
        elif sort_method == 'optimize':
            # TODO: implement this...
            # Just sort the paths from bottom to top, left to right.
            # Only the first point of the path is used as a sort key...
            path_list.sort(key=lambda cp: (cp[0].p1.y, cp[0].p1.x))
        elif sort_method == 'y+':
            # Sort by Y axis then X axis, ascending
            path_list.sort(key=lambda cp: (cp[0].p1.y, cp[0].p1.x))
        elif sort_method == 'y-':
            # Sort by Y axis then X axis, descending
            path_list.sort(key=lambda cp: (cp[0].p1.y, cp[0].p1.x),
                              reverse=True)
        elif sort_method == 'x+':
            # Sort by X axis then Y axis, ascending
            path_list.sort(key=lambda cp: cp[0].p1)
        elif sort_method == 'x-':
            # Sort by X axis then Y axis, descending
            path_list.sort(key=lambda cp: cp[0].p1, reverse=True)
        elif sort_method == 'cw_out':
            # TODO
            # Sort by geometric center moving clockwise outwards
            pass
        else:
            # do nothing for unknown sort methods...
            pass

        return path_list

    def generate_segment_gcode(self, segment, depth):
        """Generate G code for Line and Arc path segments.
        """
        # Keep track of total tool travel during feeds
        self.feed_distance += segment.length()
        # Amount of Z axis movement along this segment
        depth = getattr(segment, 'inline_z', depth)
        # Ignore the a axis tangent rotation for this segment if True
        inline_ignore_a = getattr(segment, 'inline_ignore_a', False)
        if inline_ignore_a or not self.enable_tangent:
            start_angle = self.current_angle
            end_angle = self.current_angle
            rotation = 0
        else:
            start_angle = util.seg_start_angle(segment)
            end_angle = util.seg_end_angle(segment)
            # Rotate A axis to segment start angle
            rotation = geom.calc_rotation(self.current_angle, start_angle)
            if not geom.is_zero(rotation):
                self.current_angle += rotation
                self.gc.feed(a=self.current_angle)
            # Amount of A axis rotation needed to get to end_angle.
            # The sign of the angle will determine the direction of rotation.
            rotation = geom.calc_rotation(self.current_angle, end_angle)
            # The final angle at the end of this segment
            end_angle = self.current_angle + rotation
#             logger.debug('current angle=%f' % self.current_angle)
#             logger.debug('start_angle=%f' % start_angle)
#             logger.debug('end_angle=%f' % end_angle)
#             logger.debug('rotation=%f' % rotation)
        if isinstance(segment, geom.Line):
            self.gc.feed(segment.p2.x, segment.p2.y, a=end_angle, z=depth)
        elif isinstance(segment, geom.Arc):
            r = segment.center.distance(self.gc.get_current_position_xy())
            if not geom.float_eq(r, segment.radius):
                logger = logging.getLogger(__name__)
                logger.debug('degenerate arc: r1=%f, r2=%f, %s',
                             r, segment.radius, str(segment))
#                 geom.debug.draw_arc(segment, color='#ffff00', width='1px')
                # For now just treat the f*cked up arc as a line...
                self.gc.feed(segment.p2.x, segment.p2.y, a=end_angle, z=depth)
            else:
                arcv = segment.center - segment.p1
                self.gc.feed_arc(segment.is_clockwise(),
                                 segment.p2.x, segment.p2.y,
                                 arcv.x, arcv.y, a=end_angle, z=depth)
        self.current_angle = end_angle

    def flip_tool(self):
        """Offset tangential tool rotation by 180deg.
        This useful for brush-type or double sided tools to even out wear.
        """
        # Toggle rotation direction
        self._tool_flip_toggle *= -1 # Toggle -1 and 1
        self.gc.axis_offset['A'] += self._tool_flip_toggle * math.pi

    def _flip_paths(self, path_list):
        """Preserve original path order but flip path directions
        if necessary to
        minimize rapid travel. The first path in the path list
        determines the flip order.
        """
        endp = path_list[0][-1].p2
        for path in path_list:
            d1 = endp.distance(path[0].p1)
            d2 = endp.distance(path[-1].p2)
            if d2 < d1:
                self._path_reversed(path)
            endp = path[-1].p2

    def _path_reversed(self, path):
        """Reverse in place the order of path segments.
        """
        path.reverse()
        for i, segment in enumerate(path):
            path[i] = segment.reversed()


