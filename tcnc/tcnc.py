#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
An Inkscape extension that will output G-code from
selected paths. The G-code is suitable for a CNC machine
that has a tangential tool (ie a knife or a brush).
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division, unicode_literals)
# Uncomment this if any of these builtins are used.
# from future_builtins import (ascii, filter, hex, map, oct, zip)

import os
import io
import gettext
import fnmatch
import math

# For performance measuring and debugging
import timeit
from datetime import timedelta
import logging

import geom

from geom import transform2d

from cam import gcode
from cam import paintcam
from cam import gcodesvg

from svg import geomsvg

from inkscape import inkext
from inkscape import inksvg

__version__ = '0.2.1'

_ = gettext.gettext
logger = logging.getLogger(__name__)

class Tcnc(inkext.InkscapeExtension):
    """Inkscape plugin that converts selected SVG elements into gcode
    suitable for a four axis (XYZA) CNC machine with a tangential tool,
    such as a knife or a brush, that rotates about the Z axis.
    """

    OPTIONSPEC = (
        inkext.ExtOption('--origin-ref', default='doc',
                         help=_('Lower left origin reference.')),
        inkext.ExtOption('--path-sort-method', default='none',
                         help=_('Path sorting method.')),
        inkext.ExtOption('--biarc-tolerance', type='docunits', default=0.01,
                         help=_('Biarc approximation fitting tolerance.')),
        inkext.ExtOption('--biarc-max-depth', type='int', default=4,
                         help=_('Biarc approximation maximum curve '
                               'splitting recursion depth.')),
        inkext.ExtOption('--line-flatness', type='docunits', default=0.001,
                         help=_('Curve to line flatness.')),
        inkext.ExtOption('--min-arc-radius', type='degrees', default=0.01,
                         help=_('All arcs having radius less than minimum '
                               'will be considered as straight line.')),
        inkext.ExtOption('--tolerance', type='float', default=0.00001,
                         help=_('Tolerance')),

        inkext.ExtOption('--gcode-units', default='in',
                         help=_('G code output units (inch or mm).')),
        inkext.ExtOption('--xy-feed', type='float', default=10.0,
                         help=_('XY axis feed rate in unit/s')),
        inkext.ExtOption('--z-feed', type='float', default=10.0,
                         help=_('Z axis feed rate in unit/s')),
        inkext.ExtOption('--a-feed', type='float', default=60.0,
                         help=_('A axis feed rate in deg/s')),
        inkext.ExtOption('--z-safe', type='float', default=1.0,
                         help=_('Z axis safe height for rapid moves')),
        inkext.ExtOption('--z-wait', type='float', default=500,
                         help=_('Z axis wait (milliseconds)')),
        inkext.ExtOption('--blend-mode', default='',
                         help=_('Trajectory blending mode.')),
        inkext.ExtOption('--blend-tolerance', type='float', default='0',
                         help=_('Trajectory blending tolerance.')),

        inkext.ExtOption('--disable-tangent', type='inkbool', default=False,
                         help=_('Disable tangent rotation')),
        inkext.ExtOption('--z-depth', type='float', default=-0.125,
                         help=_('Z full depth of cut')),
        inkext.ExtOption('--z-step', type='float', default=-0.125,
                         help=_('Z cutting step depth')),

        inkext.ExtOption('--tool-width', type='docunits', default=1.0,
                         help=_('Tool width')),
        inkext.ExtOption('--a-feed-match', type='inkbool', default=False,
                         help=_('A axis feed rate match XY feed')),
        inkext.ExtOption('--tool-trail-offset', type='docunits', default=0.25,
                         help=_('Tool trail offset')),
        inkext.ExtOption('--a-offset', type='degrees', default=0,
                         help=_('Tool offset angle')),
        inkext.ExtOption('--allow-tool-reversal', type='inkbool', default=False,
                         help=_('Allow tool reversal')),

        inkext.ExtOption('--tool-wait', type='float', default=0,
                         help=_('Tool up/down wait time in seconds')),

        inkext.ExtOption('--spindle-mode', default='',
                         help=_('Spindle startup mode.')),
        inkext.ExtOption('--spindle-speed', type='int', default=0,
                         help=_('Spindle RPM')),
        inkext.ExtOption('--spindle-wait-on', type='float', default=0,
                         help=_('Spindle warmup delay')),
        inkext.ExtOption('--spindle-clockwise', type='inkbool', default=True,
                         help=_('Clockwise spindle rotation')),

        inkext.ExtOption('--skip-path-count', type='int', default=0,
                         help=_('Number of paths to skip.')),
        inkext.ExtOption('--ignore-segment-angle', type='inkbool',
                         default=False, help=_('Ignore segment start angle.')),
        inkext.ExtOption('--path-tool-fillet', type='inkbool', default=False,
                         help=_('Fillet paths for tool width')),
        inkext.ExtOption('--path-tool-offset', type='inkbool', default=False,
                         help=_('Offset paths for tool trail offset')),
        inkext.ExtOption('--path-preserve-g1', type='inkbool', default=False,
                         help=_('Preserve G1 continuity for offset arcs')),
        inkext.ExtOption('--path-smooth-fillet', type='inkbool', default=False,
                         help=_('Fillets at sharp corners')),
        inkext.ExtOption('--path-smooth-radius', type='docunits', default=0.0,
                         help=_('Smoothing radius')),
        inkext.ExtOption('--path-close-polygons', type='inkbool', default=False,
                         help=_('Close polygons with fillet')),
        inkext.ExtOption('--path-split-cusps', type='inkbool', default=False,
                         help=_('Split paths at non-tangent control points')),

#         inkext.ExtOption('--brush-flip-stroke', type='inkbool', default=False,
#                          help=_('Flip brush before every stroke.')),
#         inkext.ExtOption('--brush-flip-path', type='inkbool', default=False,
#                          help=_('Flip after each path.')),
#         inkext.ExtOption('--brush-flip-reload', type='inkbool', default=False,
#                          help=_('Flip before reload.')),

        inkext.ExtOption('--brush-reload-enable', type='inkbool', default=False,
                         help=_('Enable brush reload.')),
        inkext.ExtOption('--brush-reload-rotate', type='inkbool', default=False,
                         help=_('Rotate brush before reload.')),
        inkext.ExtOption('--brush-pause-mode', default='',
                         help=_('Brush reload pause mode.')),
        inkext.ExtOption('--brush-reload-max-paths', type='int', default=1,
                         help=_('Number of paths between reload.')),
        inkext.ExtOption('--brush-reload-dwell', type='float', default=0.0,
                         help=_('Brush reload time (seconds).')),
        inkext.ExtOption('--brush-reload-angle', type='degrees', default=90.0,
                         help=_('Brush reload angle (degrees).')),
        inkext.ExtOption('--brush-overshoot-mode', default='',
                         help=_('Brush overshoot mode.')),
        inkext.ExtOption('--brush-overshoot-distance', type='docunits',
                         default=0.0, help=_('Brush overshoot distance.')),
        inkext.ExtOption('--brush-soft-landing', type='inkbool', default=False,
                         help=_('Enable soft landing.')),
        inkext.ExtOption('--brush-landing-strip', type='docunits', default=0.0,
                         help=_('Landing strip distance.')),

        inkext.ExtOption('--brushstroke-max', type='docunits', default=0.0,
                         help=_('Max brushstroke distance before reload.')),

        inkext.ExtOption('--output-path', default='~/output.ngc',
                         help=_('Output path name')),
        inkext.ExtOption('--append-suffix', type='inkbool', default=False,
                         help=_('Append auto-incremented numeric'
                         ' suffix to filename')),
        inkext.ExtOption('--separate-layers', type='inkbool', default=False,
                         help=_('Separate gcode file per layer')),

        inkext.ExtOption('--preview-toolmarks', type='inkbool', default=False,
                         help=_('Show tangent tool preview.')),
        inkext.ExtOption('--preview-scale', default='medium',
                         help=_('Preview scale.')),
                  
        inkext.ExtOption('--write-settings', type='inkbool', default=False,
                         help=_('Write Tcnc command line options in header.')),
    )

    # Document units that can be expressed as imperial (inches)
    _IMPERIAL_UNITS = ('in', 'ft', 'yd', 'pc', 'pt', 'px')
    # Document units that can be expressed as metric (mm)
    _METRIC_UNITS = ('mm', 'cm', 'm', 'km')

    _DEFAULT_DIR = '~'
    _DEFAULT_FILEROOT = 'output'
    _DEFAULT_FILEEXT = '.ngc'

    def run(self):
        """Main entry point for Inkscape plugins.
        """
        # Initialize the geometry module with tolerances and debug output
        geom.set_epsilon(self.options.tolerance)
        geom.debug.set_svg_context(self.debug_svg)

        # Create a transform to flip the Y axis.
        page_height = self.svg.get_document_size()[1]
        flip_transform = transform2d.matrix_scale_translate(1.0, -1.0,
                                                            0.0, page_height)
        timer_start = timeit.default_timer()
        skip_layers = (gcodesvg.SVGPreviewPlotter.PATH_LAYER_NAME,
                       gcodesvg.SVGPreviewPlotter.TOOL_LAYER_NAME)
        # Get a list of selected SVG shape elements and their transforms
        svg_elements = self.svg.get_shape_elements(self.get_elements(),
                                                   skip_layers=skip_layers)
        if not svg_elements:
            # Nothing selected or document is empty
            return
        # Convert SVG elements to path geometry
        path_list = geomsvg.svg_to_geometry(svg_elements, flip_transform)
        # Create the output file path name
        filepath = self.create_pathname(
            self.options.output_path, append_suffix=self.options.append_suffix)
        try:
            with io.open(filepath, 'w') as output:
                gcgen = self._init_gcode(output)
                cam = self._init_cam(gcgen)
                cam.generate_gcode(path_list)
        except IOError as error:
            self.errormsg(str(error))
        timer_end = timeit.default_timer()
        total_time = timer_end - timer_start
        logger.info('Tcnc time: %s', str(timedelta(seconds=total_time)))

    def _init_gcode(self, output):
        """Create and initialize the G code generator with machine details.
        """
        if self.options.a_feed_match:
            # This option sets the angular feed rate of the A axis so
            # that the outside edge of the brush matches the linear feed
            # rate of the XY axes when doing a simple rotation.
            # TODO: verify correctness here
            angular_rate = self.options.xy_feed / self.options.tool_width / 2
            self.options.a_feed = math.degrees(angular_rate)
        # Create G-code preview plotter.
        preview_svg_context = inksvg.InkscapeSVGContext(self.svg.document)
        preview_plotter = gcodesvg.SVGPreviewPlotter(
            preview_svg_context, tool_width=self.options.tool_width,
            tool_offset=self.options.tool_trail_offset,
            style_scale=self.options.preview_scale,
            show_toolmarks=self.options.preview_toolmarks)
        # Create G-code generator.
        gcgen = gcode.GCodeGenerator(xyfeed=self.options.xy_feed,
                                  zsafe=self.options.z_safe,
                                  zfeed=self.options.z_feed,
                                  afeed=self.options.a_feed,
                                  plotter=preview_plotter,
                                  output=output)
        gcgen.add_header_comment(('Generated by TCNC Version %s' % __version__,
                                  '',))
        # Show option settings in header
        if self.options.write_settings:
            gcgen.add_header_comment('Settings:')
            option_dict = vars(self.options)
            for option in self.OPTIONSPEC:
                val = option_dict.get(option.dest)
                if val is not None:
                    if val == None or val == option.default:
                        # Skip default settings...
                        continue
#                         valstr = '%s (default)' % str(val)
                    else:
                        valstr = str(val)
                    optname = option.dest.replace('_', '-')
                    gcgen.add_header_comment('--%s = %s' % (optname, valstr))

        # This will be 'doc', 'in', or 'mm'
        units = self.options.gcode_units
        doc_units = self.svg.get_document_units()
        if units == 'doc':
            if doc_units != 'in' and doc_units != 'mm':
                # Determine if the units are metric or imperial.
                # Pica and pixel units are considered imperial for now...
                if doc_units in self._IMPERIAL_UNITS:
                    units = 'in'
                elif doc_units in self._METRIC_UNITS:
                    units = 'mm'
                else:
                    self.errormsg(_('Document units must be imperial or metric.'))
                    raise Exception()
            else:
                units = doc_units
        unit_scale = self.svg.uu2unit('1.0', to_unit=units)
#         logger = logging.getLogger(__name__)
#         logger.debug('doc units: %s' % doc_units)
#         logger.debug('view_scale: %f' % self.svg.view_scale)
#         logger.debug('unit_scale: %f' % unit_scale)
        gcgen.set_units(units, unit_scale)
        gcgen.set_tolerance(geom.const.EPSILON)
        # For simplicity the output precision is the same as epsilon
        gcgen.set_output_precision(geom.const.EPSILON_PRECISION)
        if self.options.blend_mode:
            gcgen.set_path_blending(self.options.blend_mode,
                                 self.options.blend_tolerance)
        gcgen.spindle_speed = self.options.spindle_speed
        gcgen.spindle_wait_on = self.options.spindle_wait_on * 1000
        gcgen.spindle_clockwise = self.options.spindle_clockwise
        gcgen.spindle_auto = (self.options.spindle_mode == 'path')
        gcgen.tool_wait_down = self.options.tool_wait
        gcgen.tool_wait_up = self.options.tool_wait
        return gcgen

    def _init_cam(self, gc):
        """Create and initialize the tool path generator."""
        enable_tangent = not self.options.disable_tangent
        cam = paintcam.PaintCAM(gc)
        cam.debug_svg = self.debug_svg
        cam.z_step = self.options.z_step
        cam.z_depth = self.options.z_depth
        if self.options.path_sort_method != 'none':
            cam.path_sort_method = self.options.path_sort_method
        cam.tool_width = self.options.tool_width
        cam.tool_trail_offset = self.options.tool_trail_offset
        cam.biarc_tolerance = self.options.biarc_tolerance
        cam.biarc_max_depth = self.options.biarc_max_depth
        cam.line_flatness = self.options.line_flatness
        cam.skip_path_count = self.options.skip_path_count
        cam.enable_tangent = enable_tangent
        cam.path_tool_fillet = self.options.path_tool_fillet and enable_tangent
        cam.path_tool_offset = self.options.path_tool_offset and enable_tangent
        cam.path_preserve_g1 = self.options.path_preserve_g1 and enable_tangent
        cam.path_close_polygons = self.options.path_close_polygons and enable_tangent
        cam.path_smooth_fillet = self.options.path_smooth_fillet
        cam.path_smooth_radius = self.options.path_smooth_radius
        cam.path_split_cusps = self.options.path_split_cusps
        cam.allow_tool_reversal = self.options.allow_tool_reversal
#         cam.brush_landing_angle = self.options.brush_landing_angle
#         cam.brush_landing_end_height = self.options.brush_landing_end_height
#         cam.brush_landing_start_height = self.options.brush_landing_start_height
#         cam.brush_liftoff_angle = self.options.brush_liftoff_angle
#         cam.brush_liftoff_height = self.options.brush_liftoff_height
#         cam.brush_overshoot = self.options.brush_overshoot
        cam.brush_reload_enable = self.options.brush_reload_enable
        cam.brush_reload_rotate = self.options.brush_reload_rotate
        if self.options.brush_pause_mode in ('restart', 'time'):
            cam.brush_reload_pause = True
        if self.options.brush_pause_mode == 'time':
            cam.brush_reload_dwell = self.options.brush_reload_dwell
        else:
            cam.brush_reload_dwell = 0
        cam.brush_reload_max_paths = self.options.brush_reload_max_paths
        cam.brush_reload_angle = self.options.brush_reload_angle
#         cam.brush_reload_after_interval = self.options.brushstroke_max > 0.0
        cam.brush_depth = self.options.z_depth
        cam.brush_soft_landing = self.options.brush_soft_landing
        cam.brush_landing_strip = self.options.brush_landing_strip
        if self.options.brush_overshoot_mode == 'auto':
            cam.brush_overshoot_enable = True
            cam.brush_overshoot_auto = True
            cam.brush_overshoot_distance = cam.tool_width / 2
        elif self.options.brush_overshoot_mode == 'manual':
            cam.brush_overshoot_enable = True
            cam.brush_overshoot_distance = self.options.brush_overshoot_distance
#         if self.options.brushstroke_max > 0.0:
#             cam.feed_interval = self.options.brushstroke_max
        return cam


    def create_pathname(self, filepath, append_suffix=False):
        """Generate an absolute file path name based on the specified path.
        The pathname can optionally have an auto-incrementing numeric suffix.

        Args:
            filepath: Pathname of output file. If the directory, file name, or
                file extension are missing then defaults will be used.
            append_suffix: Append an auto-incrementing numeric suffix to the
                file name if True. Default is False.

        Returns:
            An absolute path name.
        """
        filepath = os.path.abspath(os.path.expanduser(filepath.strip()))
        filedir, basename = os.path.split(filepath)
        if not filedir:
            filedir = os.path.abspath(os.path.expanduser(self._DEFAULT_DIR))
        file_root, file_ext = os.path.splitext(basename)
        if not file_root:
            file_root = self._DEFAULT_FILEROOT
        if not file_ext:
            file_ext = self._DEFAULT_FILEEXT
        basename = file_root + file_ext # Rebuild in case of defaults
        if append_suffix:
            # Get a list of existing files that match the numeric suffix.
            # They should already be sorted.
            filter_str = '%s_[0-9]*%s' % (file_root, file_ext)
            files = fnmatch.filter(os.listdir(filedir), filter_str)
            if len(files) > 0:
                # Get the suffix from the last one and add one to it.
                # This seems overly complicated but it takes care of the case
                # where the user deletes a file in the middle of the
                # sequence, which guarantees the newest file will always
                # have the highest numeric suffix.
                last_file = files[-1]
                file_root, file_ext = os.path.splitext(last_file)
                if len(file_root) > 4:
                    try:
                        suffix = int(file_root[-4:]) + 1
                    except ValueError:
                        suffix = 0
                basename = file_root[:-4] + ('%04d' % suffix) + file_ext
            else:
                basename = file_root + '_0000' + file_ext
        return os.path.join(filedir, basename)


# _unused_options = [
#     # Unused options
#     # TODO: use or delete
#     inkext.ExtOption('--brush-landing-angle', type='degrees', default=45, help='Brushstroke landing angle.'),
#     inkext.ExtOption('--brush-overshoot', type='docunits', default=0.5, help='Brushstroke overshoot distance.'),
#     inkext.ExtOption('--brush-liftoff-height', type='float', default=0.1, help='Brushstroke liftoff height.'),
#     inkext.ExtOption('--brush-liftoff-angle', type='degrees', default=45, help='Brushstroke liftoff angle.'),
#     inkext.ExtOption('--brush-landing-start-height', type='float', default=0.1, help='Brushstroke landing start height.'),
#     inkext.ExtOption('--brush-landing-end-height', type='float', default=-0.2, help='Brushstroke landing end height.'),
#     inkext.ExtOption('--brushstroke-overlap', type='docunits', default=0.0, help='Brushstroke overlap.'),
#     inkext.ExtOption('--angle-tolerance', type='degrees', default=0.00001,
#                      help='Angle tolerance'),
#
#     inkext.ExtOption('--preview-show', type='inkbool', default=True, help='Show generated cut paths on preview layer.'),
#     inkext.ExtOption('--debug-biarcs', type='inkbool', default=True),
#
#     inkext.ExtOption('--z-offset', type='float', default=0.0, help='Offset along Z'),
#     inkext.ExtOption('--x-offset', type='float', default=0.0, help='Offset along X'),
#     inkext.ExtOption('--y-offset', type='float', default=0.0, help='Offset along Y'),
#     inkext.ExtOption('--a-offset', type='degrees', default=0.0, help='Angular offset along rotational axis'),
#     inkext.ExtOption('--z-scale', type='float', default=1.0, help='Scale factor Z'),
#     inkext.ExtOption('--x-scale', type='float', default=1.0, help='Scale factor X'),
#     inkext.ExtOption('--y-scale', type='float', default=1.0, help='Scale factor Y'),
#     inkext.ExtOption('--a-scale', type='float', default=1.0, help='Angular scale along rotational axis'),
#
#     inkext.ExtOption('--z-depth', type='float', default=-0.125, help='Z full depth of cut'),
#     inkext.ExtOption('--z-step', type='float', default=-0.125, help='Z cutting step depth'),
#     inkext.ExtOption('--gc-precision', type='float', default=0.0001,
#                      help='G code precision'),
# ]

if __name__ == '__main__':
    Tcnc().main(optionspec=Tcnc.OPTIONSPEC, flip_debug_layer=True)
