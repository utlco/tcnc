#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
Inkscape extension boilerplate class.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import os
import sys
import optparse
import math
import datetime
import gettext
import logging

from . import inksvg

_ = gettext.gettext
logger = logging.getLogger(__name__)


def _check_inkbool(dummy_option, opt_str, value):
    """Convert a string boolean (ie 'True' or 'False') to Python boolean."""
    boolstr = str(value).upper()
    if boolstr in ('TRUE', 'T', 'YES', 'Y'):
        return True
    elif boolstr in ('FALSE', 'F', 'NO', 'N'):
        return False
    else:
        errstr = 'option %s: invalid inkbool value: %s' % (opt_str, value)
        raise optparse.OptionValueError(errstr)


def _check_degrees(dummy_option, opt_str, value):
    """Convert an angle specified in degrees to radians."""
    try:
        degree_angle = float(value)
        return math.radians(degree_angle)
    except:
        errstr = 'option %s: invalid degree value: %s' % (opt_str, value)
        raise optparse.OptionValueError(errstr)

def _check_percent(dummy_option, opt_str, value):
    """Convert a percentage specified as 0-100 to a float 0-1.0."""
    try:
        return float(value) / 100
    except:
        errstr = 'option %s: invalid percent value: %s' % (opt_str, value)
        raise optparse.OptionValueError(errstr)


class ExtOption(optparse.Option):
    """Subclass of optparse.Option that adds additional type
    checkers for handling Inkscape-specific types.
    This should be used in lieu of optparse.Option for
    Inkscape extensions.
    """
    # TODO: switch to argparse...
    _EXT_TYPES = ('inkbool', 'docunits', 'degrees',)
    _EXT_TYPE_CHECKER = {'inkbool': _check_inkbool,
                         'degrees': _check_degrees,
                         'percent': _check_percent,
                         'docunits': optparse.Option.TYPE_CHECKER['float']}
    optparse.Option.TYPES = optparse.Option.TYPES + _EXT_TYPES
    optparse.Option.TYPE_CHECKER.update(_EXT_TYPE_CHECKER)
#     TYPES = optparse.Option.TYPES + ('inkbool', 'docunits', 'degrees',)
#     TYPE_CHECKER = copy.copy(optparse.Option.TYPE_CHECKER)
#     TYPE_CHECKER['inkbool'] = _check_inkbool
#     TYPE_CHECKER['degrees'] = _check_degrees
#     # This is just a placeholder since the checker needs a
#     # document unit type to convert GUI values to user units.
#     TYPE_CHECKER['docunits'] = TYPE_CHECKER['float']


class InkscapeExtension(object):
    """Base class for Inkscape extensions.
    This does not depend on Inkscape being installed and can be
    invoked as a stand-alone application.
    If an input document is not
    specified a new blank SVG document will be created.

    This replaces inkex.Effect which ships with Inkscape.

    See Also:
        inkex.Effect
    """
    # Name of debug output layer
    _DEBUG_LAYER_NAME = 'inkext_debug'

    # Built-in default extension options. These are commonly used...
    _DEFAULT_OPTIONS = (
        # This option is used by Inkscape to pass the ids of selected SVG nodes
        ExtOption('--id', action='append', dest='ids', default=[],
                  help=_('id attribute of selected objects.')),
        # Used by Inkscape extension dialog to keep track of current tab
        ExtOption('--active-tab',),
        ExtOption('--output-file', '-o',
                  help=_('Output file.')),
        ExtOption('--doc-width', type='float', default=500,
                  help=_('Document width')),
        ExtOption('--doc-height', type='float', default=500,
                  help=_('Document height')),
        ExtOption('--doc-units', default='px',
                  help=_('Document units (in, mm, px, etc)')),
        ExtOption('--create-debug-layer', type='inkbool', default=False,
                  help=_('Create debug layer')),
        ExtOption('--log-create', type='inkbool', default=False,
                  help='Create log file'),
        ExtOption('--log-level', default='DEBUG',
                  help=_('Log level')),
        ExtOption('--log-filename', default='~/inkext.log',
                  help=_('Full pathname of log file')),
    )

    def __init__(self):
        """"""
        #: Parsed command line option values available to the extension
        self.options = None
        #: SVG context for this extension
        self.svg = None
        #: Debug SVG context if a debug layer has been created
        self.debug_svg = None
        # List of selected element nodes
        self._selected_elements = []

    def main(self, optionspec=None, flip_debug_layer=False,
             debug_layer_name=None):
        """Main entry point for the extension.

        Args:
            optionspec: An optional list of :class:`optarg.Option` objects.
            flip_debug_layer: Flip the Y axis of the debug layer.
                This is useful if the GUI coordinate origin is at
                the bottom left. Default is False.
        """
        # Parse command line options
        self.options, args = self._process_options(sys.argv[1:], optionspec)
        if args:
            # Parse the SVG document from a file.
            # This may contain a document unit type
            # so this needs to be done before the options of
            # type 'docunits' can be converted to user units.
            self.svg = inksvg.InkscapeSVGContext.parse(args[0])
            # Convert 'docunits' type options to user units.
            self._post_process_options(self.options,
                                       self.svg.get_document_units())
        else:
            # Convert 'docunits' type options to user units.
            # Width and height will be needed to create the new SVG document.
            self._post_process_options(self.options, self.options.doc_units)
            # Create a new blank SVG document context
            document = inksvg.create_inkscape_document(
                            self.options.doc_width, self.options.doc_height,
                            doc_units=self.options.doc_units)
            self.svg = inksvg.InkscapeSVGContext(document)

        if debug_layer_name is None:
            self.debug_layer_name = self._DEBUG_LAYER_NAME
        else:
            self.debug_layer_name = debug_layer_name
        # Create debug log file if specified.
        # The log file name is derived from a command line option
        # so this needs to be done after option parsing.
        if getattr(self.options, 'log_create', False):
            self.create_log(getattr(self.options, 'log_filename'),
                            getattr(self.options, 'log_level'))
        # Create debug layer and context if specified
        if getattr(self.options, 'create_debug_layer', False):
            self.debug_svg = inksvg.InkscapeSVGContext(self.svg.document)
            debug_layer = self.debug_svg.create_layer(self.debug_layer_name,
                                                      flipy=flip_debug_layer)
            self.debug_svg.current_parent = debug_layer
        # Create a list of selected elements.
        # Inkscape passes a list of element node ids via the '--ids'
        # command line option.
        if getattr(self.options, 'ids', False):
            for node_id in self.options.ids:
                node = self.svg.get_node_by_id(node_id)
                self._selected_elements.append(node)
#         for opt_str in self.options.docunit_options:
#             value = self.options.docunit_options[opt_str]
#             uvalue = getattr(self.options, opt_str)
        # Run the extension
        self.run()
        # Write the output. Default is stdout.
        self.svg.write(filename=getattr(self.options, 'output_file', None))

    def run(self):
        """Extensions override this method to do the actual work."""
        pass

    def get_elements(self, selected_only=False):
        """Get selected document elements.

        Tries to get selected elements first.
        If nothing is selected and `selected_only` is False
        then <strike>either the currently selected layer or</strike>
        the document root is returned. The elements
        may or may not be visible.

        Args:
            selected_only: Get selected elements only.
                Default is False.

        Returns:
            A (possibly empty) iterable collection of elements.
        """
        elements = self._selected_elements
        if not elements and not selected_only:
            elements = self.svg.docroot
#            elements = self.svg.get_selected_layer()
#            if (elements is None or not len(elements)
#                    or not self.svg.node_is_visible(elements)):
#                elements = self.svg.docroot
        return elements

    def errormsg(self, msg):
        """Intended for end-user-visible error messages.
        Inkscape displays stderr output with an error dialog.
        """
        sys.stderr.write((unicode(msg) + "\n").encode("UTF-8"))

    def create_log(self, log_path=None, log_level='DEBUG'):
        """Create a log file for debug output.

        Args:
            log_path: Path to log file. If None or empty
                the log path name will be the
                command line invocation name (argv[0]) with
                a '.log' suffix in the user's home directory.
            log_level: Log level:
                'DEBUG', 'INFO', 'WARNING', 'ERROR', or 'CRITICAL'.
                Default is 'DEBUG'.
        """
        if log_path is None or not log_path:
            log_dir = os.path.expanduser('~')
            log_path = os.path.join(log_dir, sys.argv[0] + '.log')
        log_path = os.path.expanduser(log_path)
        logging.basicConfig(filename=os.path.abspath(log_path),
                            filemode='w', level=log_level.upper())
        logger = logging.getLogger(__name__)
        logger.info('Log started %s, level=%s', datetime.datetime.now(),
                    logging.getLevelName(logger.getEffectiveLevel()))

    def _process_options(self, argv, optionspec):
        """Set up option spec and parse command line options.

        """
        # This option checking function needs the SVG document context
        # before being defined.
        # It converts 'document' UI units to SVG user units.
#         def _check_docunits(dummy_option, dummy_opt_str, value):
#             return self.svg.unit2uu(value, from_unit=self.svg.doc_units)
        docunit_options = {}
        def _check_docunits(option, dummy_opt_str, value):
            docunit_options[option.dest] = float(value)
            return value

        ExtOption.TYPE_CHECKER['docunits'] = _check_docunits
        option_parser = optparse.OptionParser(
            usage='usage: %prog [options] [file]',
            option_list=self._DEFAULT_OPTIONS,
            option_class=ExtOption)
        if optionspec is not None:
            for option in optionspec:
                option_parser.add_option(option)
        options, args = option_parser.parse_args(argv)
        options.docunit_options = docunit_options
        return (options, args)

    def _post_process_options(self, options, doc_units):
        """
        Options values that are of type 'docunits' will be converted
        to SVG user units.
        """
        # This needs to be done after the SVG document is parsed
        # so that the document unit can be determined.
        # If it's a new document then the unit type is hopefully
        # specified as a command line option. If not, a default
        # will be used.
        if doc_units is None or not doc_units:
            doc_units = 'px'
        for opt_str in options.docunit_options:
            value = options.docunit_options[opt_str] # getattr(options, opt_str)
            uu_value = self.svg.unit2uu(value, from_unit=doc_units)
            setattr(options, opt_str, uu_value)

