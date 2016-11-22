#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
A G-code generator that is suitable for a four axis (or 3.5 axis)
machine with X, Y, and Z axes along with an angular A
axis that rotates about the Z axis. It is more general but
that's the machine I have and the code might reflect that.

The generated G code is currently intended for a LinuxCNC
interpreter, but probably works fine for others as well.

====
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import math
import datetime
import logging
import gettext

_ = gettext.gettext


class PreviewPlotter(object):
    """Base interface that can be implemented by users of the GCode
    class to provide a graphical preview of the G-code output.

    See :py:mod:`cam.gcodesvg` for an example of an SVG implemention.
    """

    def __init__(self):
        # An instance of GCode. Set by GCodeGenerator.
        self.gcgen = None

    def plot_move(self, endp):
        """Plot G00 - rapid move from current tool location to to ``endp``.

        Args:
            endp: Endpoint of move as a 4-tuple (x, y, z, a).
        """
        pass

    def plot_feed(self, endp):
        """Plot G01 - linear feed from current tool location to ``endp``.

        Args:
            endp: Endpoint of feed as a 4-tuple (x, y, z, a).
        """
        pass

    def plot_arc(self, center, endp, clockwise):
        """Plot G02/G03 - arc feed from current tool location to to ``endp``.

        Args:
            center: Center of arc as  a 2-tuple (x, y)
            endp: Endpoint of feed as a 4-tuple (x, y, z, a).
            clockwise: True if the arc moves in a clockwise direction.
        """
        pass


class GCodeException(Exception):
    """Exception raised by gcode generator."""
    pass


class GCodeGenerator(object):
    """GCode generator class that describes a basic two axis (XY),
    three axis (XYZ), or four axis (XYZA)
    machine. The G code output is compatible with LinuxCNC.

    Angles are always specified in radians but output as degrees.

    Axis values are always specified in user/world coordinates and output
    as machine units (ie inches or millimeters) using ``GCode.unit_scale``
    as the scaling factor.
    """

    #: Current machine target
    TARGET = 'linuxcnc'

    # Target machine info - machine name, version
    _TARGET_INFO = {'linuxcnc': ('LinuxCNC', '2.4+'),}
    # Order in which G code parameters are specified in a line of G code
    _GCODE_ORDERED_PARAMS = 'XYZUVWABCIJKRDHLPQSF'
    # Non-modal G codes (LinuxCNC.)
    _GCODE_NONMODAL_GROUP = ('G04', 'G10', 'G28', 'G30', 'G53', 'G92')
    # G codes where a feed rate is required
    _GCODE_FEED = ('G01', 'G02', 'G03')
    # G codes that change the position of the tool
    _GCODE_MOTION = ('G00', 'G01', 'G02', 'G03')
    # G codes that are suppressed if the parameters remain unchanged
    _GCODE_MODAL_MOTION = ('G00', 'G01', 'G02', 'G03')
    # Default tolerance for floating point comparison
    _DEFAULT_TOLERANCE = 1e-6
    # Maximum reasonable precision
    _MAX_PRECISION = 15
    # Minimum reasonable precision
    _MIN_PRECISION = 2

    def __init__(self, xyfeed, zsafe, zfeed=None, afeed=None,
                 output=None, plotter=None):
        """
        Args:
            xyfeed: Default feed rate along X and Y axes,
                in machine units per minute.
            zsafe: The safe height of the Z axis for rapid XY moves.
            zfeed: Feed rate along Z axis
                in machine units per minute.
                (Defaults to `xyfeed`.)
            afeed: Feed rate along A axis in degrees per minute.
                (Defaults to `xyfeed`.)
            output: Output stream for generated G code.
                Must implement ``write()`` method.
                Defaults to a StringIO if None (default).
            plotter: Preview plotter. Should be a subclass of
                ``gcode.PreviewPlotter``.
        """
        #: Feed rate along X and Y axes
        self.xyfeed = xyfeed
        #: Z axis safe height for rapid moves
        self.zsafe = zsafe
        #: Z axis feed rate
        self.zfeed = zfeed
        #: Angular axis feed rate
        self.afeed = afeed
        #: Current line number
        self.line_number = 0
        #: The G code output stream
        self.output = output
        #: The current preview plotter
        self.preview_plotter = plotter
        #: User to machine unit scale
        self.unit_scale = 1.0
        #: Tolerance for float comparisons
        self.tolerance = self._DEFAULT_TOLERANCE
        #: Tolerance for angle comparisons
        self.angle_tolerance = self._DEFAULT_TOLERANCE
        #: Delay time in millis for tool-down
        self.tool_wait_down = 0.0
        #: Delay time in millis for tool-up
        self.tool_wait_up = 0.0
        #: Alternate G code for Tool Up
        self.alt_tool_up = None
        #: Alternate G code for Too Down
        self.alt_tool_down = None
        #: Default delay time in milliseconds after spindle is turned on.
        self.spindle_wait_on = 0.0
        #: Default delay time in milliseconds after spindle is shut off.
        self.spindle_wait_off = 0.0
        #: Spindle direction flag
        self.spindle_clockwise = True
        #: Default spindle speed
        self.spindle_speed = 0.0
        #: Turn spindle on/off automatically on tool_up/tool_down
        self.spindle_auto = False
        #: Angles < 360 ?
        self.wrap_angles = False
        #: Show comments if True
        self.show_comments = True
        #: Show line numbers if True
        self.show_line_numbers = False
        #: Extra header comments
        self.header_comments = []
        #: Blend mode. Can be None, 'blend', or 'exact'.
        # See <http://linuxcnc.org/docs/2.4/html/common_User_Concepts.html#r1_1_1>
        self.blend_mode = None
        #: Blend tolerance. P value for G64 blend directive.
        self.blend_tolerance = None
        #: Naive cam detector tolerance value. Q value for G64 blend directive.
        self.blend_qtolerance = None
        #: Output code comments
        self.verbose = False

        if self.zfeed is None:
            self.zfeed = self.xyfeed
        if self.afeed is None:
            self.afeed = self.xyfeed
        if self.output is None:
            import StringIO
            self.output = StringIO.StringIO()
        if self.preview_plotter is None:
            self.preview_plotter = PreviewPlotter()

        # Pass this instance along to the preview plotter
        if self.preview_plotter is not None:
            self.preview_plotter.gcgen = self

        # GCode output units
        self._units = 'in'
        # Last value for G code parameters
        self._last_val = {} #{'X': 0.0, 'Y': 0.0, 'Z': 0.0, 'A': 0.0, 'F': 0.0}
        for param in self._GCODE_ORDERED_PARAMS:
            self._last_val[param] = None
        # True if the tool is above the Z axis safe height for rapid moves
        self._is_tool_up = False
        # Default epsilon and output precision
        self.set_tolerance(self._DEFAULT_TOLERANCE)
        precision = int(round(abs(math.log(self._DEFAULT_TOLERANCE, 10))))
        self.set_output_precision(precision)
        # Axis scale factors
        self._axis_scale = {}
        # Axis offsets
        self._axis_offset = {}
        # Map canonical axis names to G code output names.
        # Values can be changed to accomodate machines that expect
        # different axis names (ie. using C instead of A or UVW instead of XYZ)
        self._axis_map = {}
        # Flag set when the axis angle has been normalized
        self._axis_offset_reset = False

    @property
    def units(self):
        """GCode output units. Can be 'in' or 'mm'."""
        return self._units

    @units.setter
    def units(self, value):
        if not value in ('in', 'mm'):
            raise GCodeException('Units must be "in" or "mm".')
        self._units = value

    @property
    def X(self):
        """The current X axis value or none if unknown."""
        return self._last_val['X']

    @property
    def Y(self):
        """The current Y axis value or none if unknown."""
        return self._last_val['Y']

    @property
    def Z(self):
        """The current Z axis value or none if unknown."""
        return self._last_val['Z']

    @property
    def A(self):
        """The current A axis value or none if unknown."""
        return self._last_val['A']

    def set_tolerance(self, tolerance, angle_tolerance=None):
        """Set tolerance (epsilon) for floating point comparisons.

        Args:
            tolerance: The tolerance for scalar floating point comparisons
                except angular values.
            angle_tolerance: The tolerance for comparing angle values. Set to
                ``tolerance`` if None (default).
        """
        self.tolerance = tolerance
        if angle_tolerance is None:
            angle_tolerance = tolerance
        self.angle_tolerance = angle_tolerance

    def set_output_precision(self, precision):
        """Set numeric output precision. This determines the
        number of digits after the decimal point.

        This can be different from the precision implied
        by the `tolerance` value. The default is derived
        from the `tolerance` value.

        Args:
            precision: The number of digits after the decimal point.
        """
        ndigits = max(min(int(precision),
                          self._MAX_PRECISION), self._MIN_PRECISION)
        self._fmt_float = '%%.%df' % ndigits

    def set_units(self, units, unit_scale=1.0):
        """Set G code units and unit scale factor.

        Note:
            Linear axis values are specified in user/world coordinates
            and output as machine units (ie inches or millimeters)
            using ``unit_scale`` as the scaling factor to scale from
            user/world units to G-code units.

        Args:
            units: Unit specifier. Must be `'in'` or `'mm'`.
            unit_scale: Scale factor to apply to linear axis values.
                Default is 1.0.
        """
        if units not in ('in', 'mm'):
            raise GCodeException(_('Units must be mm or in.'))
        self.units = units
        self.unit_scale = unit_scale

    def set_spindle_defaults(self, speed, clockwise=True,
                             wait_on=0, wait_off=0, auto=False):
        """Set spindle parameter defaults.

        Args:
            speed: Spindle speed in RPM
            clockwise: Spindle direction. True if clockwise (default).
            wait_on: Number of milliseconds to wait for the spindle to reach
                full speed.
            wait_off: the number of milliseconds to wait for the spindle
                to stop.
            auto: Turn on/off spindle automatically on
                :py:meth:`tool_up()`/:py:meth:`tool_down()`.
                Default is False.
        """
        self.spindle_speed = speed
        self.spindle_clockwise = clockwise
        self.spindle_wait_on = wait_on
        self.spindle_wait_off = wait_off
        self.spindle_auto = auto

    def set_path_blending(self, mode, tolerance=None, qtolerance=None):
        """Set path trajectory blending mode and optional tolerance.

        Args:
            mode: Path blending mode. Can be 'exact' or 'blend'.
                Uses *G64* in 'blend' mode and *G61* in 'exact' mode.
            tolerance: Blending tolerance. Only used in 'blend' mode.
                This is the value for the G64 *P* parameter.
                Default is None.
            qtolerance: Naive cam detector tolerance value.
                This is the value for the G64 *Q* parameter.
                Default is None.
        """
        if mode.upper() == 'G61':
            mode = 'exact'
        elif mode.upper() == 'G64':
            mode = 'blend'
        if mode in ('exact', 'blend'):
            self.blend_mode = mode
            self.blend_tolerance = tolerance
            self.blend_qtolerance = qtolerance
        # ignore anything else...

    def set_axis_offset(self, **kwargs):
        """Set the offset for the specified axes.

        Axis offsets are always specified in *machine units*.
        Angular offsets are always in *degrees*.

        This is a 'soft' offset, not a G92 offset. The offset
        value will be added to the current axis value when
        a move is performed.

        Example::

            gcode_gen = gcode.GCodeGenerator(...)
            gcode_gen.set_axis_offset(x=10, y=10)

        Args:
            x: X axis offset value (optional)
            y: Y axis offset value (optional)
            z: Z axis offset value (optional)
            a: A axis offset value (optional)
        """
        for axis in kwargs:
            self._axis_offset[axis.upper()] = float(kwargs.get(axis))

    def set_axis_scale(self, **kwargs):
        """Set the scaling factors for the specified axes.
        The scaling is applied before the world/machine unit scaling.

        Example::

            gcode_gen = gcode.GCodeGenerator(...)
            gcode_gen.set_axis_scale(x=10, y=10)

        Args:
            x: X axis scale value (optional)
            y: Y axis scale value (optional)
            z: Z axis scale value (optional)
            a: A axis scale value (optional)
        """
        for axis in kwargs:
            self._axis_scale[axis.upper()] = float(kwargs.get(axis))

    def map_axis(self, canonical_name, output_name):
        """Map canonical axis names to G code output names.

        Mapping can be used to accommodate machines that expect
        different axis names (ie. using C instead of A or UVW instead of XYZ).

        Args:
            canonical_name: Canonical axis name.
                (ie 'X', 'Y', 'Z', or 'A')
            output_name: Output name.
                (ie 'U', 'V', 'W', or 'C')
        """
        self._axis_map[canonical_name.upper()] = output_name.upper()

    def add_header_comment(self, comment):
        """Append a comment to the header section.

        Args:
            comment: A comment or list of comments.
        """
        self.header_comments.append(comment)

    def comment(self, comment=None):
        """Write a G code comment line.

        Encloses the comment string in parentheses.
        Outputs a newline if the comment string is None (default).

        Args:
            comment: A comment string or a list (or tuple) of comment strings.
                In the case of multiple comments, each one will be
                on a separate line.
        """
        if comment is None:
            self._write('\n')
        elif self.show_comments:
            if not hasattr(comment, 'strip') and hasattr(comment, '__iter__'):
                for comment_line in comment:
                    self._write_comment(comment_line)
            else:
                self._write_comment(comment)

    def header(self, comment=None):
        """Output a pretty standard G code file header.

        Args:
            comment: A header comment or a list of comments (optional).
        """
        self._write('%\n')
        self.comment('--------------------------------------------------------')
        today_str = datetime.datetime.today().isoformat(b' ')
        self.comment(_('Creation date: %s') % today_str)
        self.comment(_('Target machine: %s, version %s') % \
                     (self._TARGET_INFO[self.TARGET][0],
                      self._TARGET_INFO[self.TARGET][1]))
        if self.header_comments:
            for header_comment in self.header_comments:
                self.comment(header_comment)
        if comment is not None:
            self.comment(comment)
        self.comment('--------------------------------------------------------')
        self._write('\n')
        self._write_line('G17', _('XY plane'))
        if self.units == 'mm':
            self._write_line('G21', _('Units are in millimeters'))
        else:
            self._write_line('G20', _('Units are in inches'))
        self._write_line('G90', _('Use absolute positioning'))
        self._write_line('G40', _('Cancel tool diameter compensation'))
        self._write_line('G49', _('Cancel tool length compensation'))
        if self.blend_mode == 'blend':
            if self.blend_tolerance is None:
                self._write_line('G64', comment=_('Blend with highest speed'))
            else:
                p_value = self._fmt_float % self.blend_tolerance
                if self.blend_qtolerance is not None:
                    q_value = self._fmt_float % self.blend_qtolerance
                    self._write_line('G64 P%s Q%s' % (p_value, q_value),
                                     comment=_('Blend with tolerances'))
                else:
                    self._write_line('G64 P%s' % p_value,
                                     comment=_('Blend with tolerance'))
        elif self.blend_mode == 'exact':
            self._write_line('G61', comment=_('Exact path mode'))
        self._write('\n')
        self.comment(_('Default feed rate'))
        self.feed_rate(self.xyfeed)
        self._write('\n\n')

    def footer(self):
        """Output a generic G code file footer."""
        self._write('\n')
        if self._axis_offset_reset and self.TARGET == 'linuxcnc':
            self.gcode_command('G92.1', comment='Reset axis offsets to zero')
        self._write_line('M2', _('End program.'))
        self._write('%\n')

    def feed_rate(self, feed_rate):
        """Set the specified feed rate. Outputs the *F* G code directive
        if the feed rate has changed since the last feed value.

        Args:
            feed_rate: The feed rate in machine units per minute.
        """
        if self._last_val['F'] is None \
        or not self.float_eq(feed_rate - self._last_val['F']):
            self._write_line('F%s' % (self._fmt_float % feed_rate))
            self._last_val['F'] = feed_rate

    def pause(self, conditional=False, comment='Pause'):
        """Pause the G code interpreter.

        Outputs *M1* or *M0* G code.

        Note:
            Normally, pressing the start button in LinuxCNC/Axis
            will restart the interpreter after a pause.

        Args:
            conditional: use conditional stop if True.
            comment: Optional comment string.
        """
        mcode = 'M1' if conditional else 'M0'
        self.gcode_command(mcode, comment=comment)

    def dwell(self, milliseconds, comment=None):
        """Output a dwell command which pauses the tool for the specified
        number of milliseconds.

        Args:
            milliseconds: Number of milliseconds to pause.
            comment: Optional comment string.
        """
        # LinuxCNC interprets P as seconds whereas pretty much everything else
        # (ie Fanuc) interprets the parameter as milliseconds...
        if milliseconds > 0:
            if self.TARGET == 'linuxcnc':
                seconds = milliseconds / 1000.0
                if comment is None:
                    comment = _('Pause tool for %.4f seconds') % seconds
                self._write_line('G04 P%.4f' % seconds, comment=comment)
            else:
                if comment is None:
                    comment = _('Pause tool for %d milliseconds') % milliseconds
                self._write_line('G04 P%d' % milliseconds, comment=comment)

    def tool_up(self, rapid=True, wait=None, comment=None):
        """Moves tool to a safe Z axis height.
        This should be called before performing a rapid move.

        The spindle will also be automatically shut off
        if ``Gcode.spindle_auto`` is True.

        Args:
            rapid: Use G0 to move Z axis, otherwise G1 at current feed rate.
                Default is True.
            wait: the number of milliseconds to wait for the tool to retract.
                Uses GCode.tool_wait_up value by default if None specified.
                This parameter is mainly useful for pneumatically
                controlled up/down axes where the actuator may take
                a few milliseconds to extend/retract.
            comment: Optional comment string.
        """
        # Note: self._is_tool_up is purposely not checked here to insure
        # that the tool is forced to a safe height regardless of internal state
        if self.alt_tool_up is not None:
            self.gcode_command(self.alt_tool_up)
        else:
            cmd = 'G00' if rapid else 'G01'
            self.gcode_command(cmd, Z=self.zsafe, force_value='Z',
                               comment=comment)
        if self.spindle_auto:
            self.spindle_off()
        if wait is None:
            wait = self.tool_wait_up
        if wait > 0:
            self.dwell(wait)
        self._is_tool_up = True

    def tool_down(self, z, feed=None, wait=None, comment=None):
        """Moves tool on Z axis down to specified height.
        Outputs a *G1* move command using the current feed rate for the
        Z axis.

        The spindle will be automatically turned on first
        if ``Gcode.spindle_auto`` is True.

        Args:
            z: Height of Z axis to move to.
            feed: Feed rate (optional - default Z axis feed rate used if None.)
            wait: the number of milliseconds to wait for the tool to
                actually get to the specified depth.
                Uses `GCode.tool_wait_down` value by default if None specified.
                This parameter is mainly useful for pneumatically
                controlled up/down axes where the actuator may take
                a few milliseconds to extend/retract.
            comment: Optional comment string.
        """
        if feed is None:
            feed = self.zfeed
        if wait is None:
            wait = self.tool_wait_down
        if self.spindle_auto:
            self.spindle_on()
        if self.alt_tool_down is not None:
            self.gcode_command(self.alt_tool_down)
        else:
            self.gcode_command('G01', Z=z, F=feed, comment=comment)
        self._is_tool_up = False
        if wait > 0:
            self.dwell(wait)

    def spindle_on(self, speed=None, clockwise=None, wait=None, comment=None):
        """Turn on the spindle.

        Args:
            speed: Spindle speed in RPM.
                If None use default speed.
            clockwise: Spindle turns clockwise if True.
                If None use default value.
            wait: Number of milliseconds to wait for the spindle to reach
                full speed. Uses ``GCode.spindle_wait_on`` value by default.
            comment: Optional comment string.
        """
        if speed is None:
            speed = self.spindle_speed
        if clockwise is None:
            clockwise = self.spindle_clockwise
        if wait is None:
            wait = self.spindle_wait_on
        mcode = 'M3' if clockwise else 'M4'
        self._write_line('%s S%d' % (mcode, int(speed)), comment=comment)
        if wait > 0.0:
            self.dwell(wait)

    def spindle_off(self, wait=None, comment=None):
        """Turn off the spindle.

        Args:
            wait: the number of milliseconds to wait for the spindle
                to stop. Uses ``GCode.spindle_wait_off`` value by default.
            comment: Optional comment string.
        """
        self._write_line('M5', comment=comment)
        if wait is None:
            wait = self.spindle_wait_off
        if wait > 0.0:
            self.dwell(wait)

    def normalize_axis_angle(self, axis='A'):
        """Unwrap (normalize) a rotational axis.
        If the current angular position of the axis is > 360 this will
        reset the rotary axis origin so that 0 < angle < 360.

        Useful when cutting large spirals with a tangent knife to minimize
        long unwinding moves between paths.

        Args:
            axis: Name of axis to unwrap. Default is 'A'.
        """
        axis = axis.upper()
        if axis not in 'ABC':
            raise GCodeException(_('Can only normalize a rotational axis.'))
        angle = self._last_val[axis]
        if abs(angle) > 2*math.pi:
            # normalize the angle
            angle = angle - 2*math.pi * math.floor(angle / 2*math.pi)
            val = self._fmt_float % math.degrees(angle)
            self._write_line('G92 %s=%s' % (axis, val),
                             comment=_('Normalize axis angle'))
            self._last_val[axis] = angle
            self._axis_offset_reset = True

    def rapid_move(self, x=None, y=None, z=None, a=None, comment=None):
        """Perform a rapid *G0* move to the specified location.

        At least one axis should be specified.
        If the tool is below the safe 'Z' height it will be raised before
        the rapid move is performed.

        Args:
            x: X axis value (optional)
            y: Y axis value (optional)
            z: Z axis value (optional)
            a: A axis value (optional)
            comment: Optional comment string.
        """
        # Make sure the tool is at a safe height for a rapid move.
        z_position = self.position('Z')
        if z_position is None or z_position < self.zsafe or self._is_tool_up:
            self.tool_up()
        z = max(self.zsafe, z)
        self.gcode_command('G00', X=x, Y=y, Z=z, A=a, comment=comment)
        self.preview_plotter.plot_move(self._endp(x, y, z, a))

    def feed(self, x=None, y=None, z=None, a=None, feed=None, comment=None):
        """Perform a *G1* linear tool feed to the specified location.

        At least one axis should be specified.

        Args:
            x: X axis value (optional)
            y: Y axis value (optional)
            z: Z axis value (optional)
            a: A axis value (optional)
            feed: Feed rate (optional - default feed rate used if None)
            comment: Optional comment string.
        """
        # Determine default feed rate appropriate for the move
        if feed is None:
            if x is not None or y is not None:
                feed = self.xyfeed
            elif z is not None:
                feed = self.zfeed
            elif a is not None:
                feed = self.afeed
            else:
                # No feed rate, no axis specified - nothing to feed
                return
        self.gcode_command('G01', X=x, Y=y, Z=z, A=a, F=feed, comment=comment)
        self.preview_plotter.plot_feed(self._endp(x, y, z, a))

    def feed_arc(self, clockwise, x, y, arc_x, arc_y, a=None, z=None,
                 feed=None, comment=None):
        """Perform a *G2*/*G3* arc feed.

        This will raise a GCodeException if the beginning and ending arc radii
        do not match, ie if one of the end points does not lie on the arc.

        Args:
            clockwise: True if the arc moves in a clockwise direction.
            x: X value of arc end point
            y: Y value of arc end point
            arc_x: Center of arc relative to ``x``
            arc_y: Center of arc relative to ``y``
            a: A axis value at endpoint (in radians)
            feed: Feed rate (optional - default feed rate used if None)
            comment: Optional comment string.
        """
        # Make sure that both the start and end points lie on the arc.
        current_xy = self.get_current_position_xy()
        center = (arc_x + current_xy[0], arc_y + current_xy[1])
        # Distance from center to current position
        start_radius = math.hypot(current_xy[0] - center[0],
                                  current_xy[1] - center[1])
        end_radius = math.hypot(arc_x, arc_y)
        if not self.float_eq(start_radius, end_radius):
            logger = logging.getLogger(__name__)
            logger.debug('Degenerate arc:')
            logger.debug('  start point = (%f, %f), end point = (%f, %f)',
                         current_xy[0], current_xy[1], x, y)
            logger.debug('  start radius = %f, end radius = %f',
                         start_radius, end_radius)
            raise GCodeException('Mismatching arc radii.')
        gcode = 'G02' if clockwise else 'G03'
        self.gcode_command(gcode, X=x, Y=y, Z=z, I=arc_x, J=arc_y, A=a,
                           F=(feed if feed is not None else self.xyfeed),
                           force_value='IJ',
                           comment=comment)
        self.preview_plotter.plot_arc(center, self._endp(x, y, z, a), clockwise)

    def get_current_position_xy(self):
        """The last known tool position on the XY plane.

        Returns:
            A 2-tuple containing coordinates of X and Y axes
            of the form (X, Y). An axis value will be
            None if the position is unknown.
        """
        return (self._last_val['X'], self._last_val['Y'])

    def get_current_position(self):
        """The last known tool position.

        Returns:
            A 4-tuple containing coordinates of all four axes
            of the form (X, Y, Z, A). An axis value will be
            None if the position is unknown.
        """
        return (self._last_val['X'], self._last_val['Y'],
                self._last_val['Z'], self._last_val['A'],)

    def position(self, axis):
        """The current position of the specified axis.

        Args:
            axis: The axis name - i.e. 'X', 'Y', 'Z', 'A', etc.

        Returns:
            The current position of the named axis as a float value.
        """
        axis = axis.upper()
        if axis not in self._last_val:
            raise GCodeException('Undefined axis %s' % axis)
        return self._last_val[axis]

    def gcode_command(self, command, **kwargs):
        """Output a line of gcode.

        This is mainly for internal use and should be
        used with extreme caution.
        Use the higher level methods if at all possible.

        Args:
            command: G code command. Required.
            params: Parameter string that will be output as is.
                This `must not` be used with commands that
                that may change the position of the machine. Optional.
            X: The X axis value. Optional.
            Y: The Y axis value. Optional.
            Z: The Z axis value. Optional.
            I: Center (x) of arc relative to X,Y. Optional.
            J: Center (y) of arc relative to X,Y. Optional.
            R: Arc radius. Optional.
            A: The A axis value in radians. Optional.
            force_value: A string containing the modal parameter names
                whose values will be output regardless of whether their
                values have changed.
                By default if the specified value of a modal parameter has not
                changed since its last value then it will not be output.
            comment: Optional inline comment string.

        Raises:
            GCodeException
        """
        if command is None or not command:
            return
        command = _canonical_cmd(command)
        base_cmd = command.split('.')[0]
        params = kwargs.get('params')
        comment = kwargs.get('comment')
        # Make sure motion can be tracked.
        if command in self._GCODE_MOTION and params is not None and params:
            raise GCodeException('Motion command with opaque parameters.')
        pos_params = dict()
        force_value = kwargs.get('force_value', '')
        # Extract machine position parameters and update
        # internal position coordinates.
        for k in ('X', 'Y', 'Z', 'I', 'J', 'R', 'A', 'F'):
            value = kwargs.get(k)
            if value is not None:
                if k in 'ABC':
                    # Use angle tolerance for comparing angle values
                    tolerance = self.angle_tolerance
                    if self.wrap_angles:
                        value = math.fmod(value, 2*math.pi)
                else:
                    # Otherwise use float tolerance
                    tolerance = self.tolerance
                value_has_changed = (self._last_val[k] is None or
                                     abs(value - self._last_val[k]) > tolerance)
                gcode_is_nonmodal = base_cmd in self._GCODE_NONMODAL_GROUP
                if k in force_value or value_has_changed or gcode_is_nonmodal:
                    self._last_val[k] = value
                    # Apply any axis transforms
                    value *= self._axis_scale.get(k, 1.0)
                    value += self._axis_offset.get(k, 0.0)
                    if k in 'ABC':
                        value = math.degrees(value)
                    elif k in 'XYZIJ':
                        # Tool height safety check
                        if k == 'Z' and self._is_tool_up and value < self.zsafe:
                            self._is_tool_up = False
                        # Apply unit scale (user/world to machine units)
                        value *= self.unit_scale
                    pos_params[k] = value

        gcode_line = None
        if len(pos_params) > 0:
            # Suppress redundant feedrate-only lines
            if len(pos_params) > 1 or 'F' not in pos_params:
                line_parts = [command,]
                # Arrange the parameters in a readable order
                for k in self._GCODE_ORDERED_PARAMS:
                    value = pos_params.get(k)
                    if value is not None:
                        k = self._axis_map.get(k, k)
                        line_parts.append('%s%s' % (k, self._fmt_float % value))
                gcode_line = ' '.join(line_parts)
        # Note: this check will suppress output of modal commands
        # with unchanged parameter values.
        elif base_cmd not in self._GCODE_MODAL_MOTION:
            gcode_line = command
            if params is not None and params:
                gcode_line += ' ' + params
        if gcode_line is not None:
            self._write_line(gcode_line, comment=comment)

    def _write_line(self, line='', comment=None):
        """Write a (optionally numbered) line to the G code output.
        A newline character is always appended, even if the string is empty.

        Empty lines and comment-only lines are not numbered.
        """
        if line is not None and line:
            if self.show_line_numbers:
                self._write('N%d ' % self.line_number)
                self.line_number += 1
            self._write(line)
        if self.show_comments and comment:
            if line is not None and line:
                self._write(' ')
            self._write('(%s)' % comment)
        self._write('\n')

    def _write_comment(self, comment):
        """Write a comment string and newline to the gcode output stream."""
        if comment is None:
            self._write('\n')
        else:
            self._write('(%s)\n' % comment)

    def _write(self, text):
        """Write the string to the gcode output stream."""
        self.output.write(text)

    def _endp(self, x, y, z, a):
        """Return the end point of the current trajectory.
        Used for preview plotting."""
        return (x if x is not None else self._last_val['X'],
                y if y is not None else self._last_val['Y'],
                z if z is not None else self._last_val['Z'],
                a if a is not None else self._last_val['A'])

    def float_eq(self, a, b):
        """Compare two floats for approximate equality within the tolerance
        specified for the GCodeGenerator class.
        """
        return abs(a - b) < self.tolerance


def _canonical_cmd(cmd):
    """Canonicalize a G code command.
    Converts to upper case and expands shorthand (ie. G1 to G01)."""
    cmd = cmd.upper()
    if len(cmd) == 2 and cmd[1].isdigit():
        cmd = cmd[0] + '0' + cmd[1]
    return cmd

