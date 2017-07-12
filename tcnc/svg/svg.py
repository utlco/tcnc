#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
A simple library for SVG output.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import sys
import math
import numbers
import re
import string
import random
import logging

from lxml import etree

from geom import transform2d

from . import css

# For debugging...
logger = logging.getLogger(__name__)

# : SVG Namespaces
SVG_NS = {
#     None: u'http://www.w3.org/2000/svg',
    u'svg': u'http://www.w3.org/2000/svg',
    u'xlink': u'http://www.w3.org/1999/xlink',
    u'xml': u'http://www.w3.org/XML/1998/namespace'
}

def _add_ns(tag, ns_map, ns):
    return '{%s}%s' % (ns_map[ns], tag)

def svg_ns(tag):
    """Shortcut to prepend SVG namespace to `tag`."""
    return _add_ns(tag, SVG_NS, 'svg')

def xml_ns(tag):
    """Shortcut to prepend XML namespace to `tag`."""
    return _add_ns(tag, SVG_NS, 'xml')

def xlink_ns(tag):
    """Shortcut to prepend xlink namespace to `tag`."""
    return _add_ns(tag, SVG_NS, 'xlink')

def strip_ns(tag):
    """Strip the namespace part from the tag if any."""
    return tag.rpartition('}')[2]


class SVGContext(object):
    """SVG document context.
    """
    # Default floating point output precision.
    # Number of digits after the decimal point.
    _DEFAULT_PRECISION = 5

    # A dictionary of explicit unit to px, or user unit, conversion factors
    # See http://www.w3.org/TR/SVG/coords.html#Units
    _UU_CONV = {
        # em and ex should be determined by CSS
        'em': 12.5, 'ex': 12.5,
        'px': 1.0, 'pt': 1.25, 'pc': 15.0,
        'mm': 3.543307, 'cm': 35.43307, 'in': 90.0,
        # These are non-standard
        'm': 3543.307, 'ft': 1080, 'yd': 3240,
    }
    # Pre-compiled REs for parsing unit specifiers.
    _UU_UNIT = re.compile('(%s)$' % '|'.join(_UU_CONV.keys()))
    _UU_FLOAT = re.compile(r'(([-+]?[0-9]+(\.[0-9]*)?|[-+]?\.[0-9]+)([eE][-+]?[0-9]+)?)')
    # Pre-compiled RE for parsing SVG transform attribute value.
    _TRANSFORM_RE = re.compile(r'(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)\s*,?',
                               re.IGNORECASE)

    # Float comparison tolerance
    _epsilon = math.pow(10.0, -_DEFAULT_PRECISION)

    @classmethod
    def create_document(cls, width, height, doc_id=None, doc_units=None):
        """Create a minimal SVG document.

        Returns:
            An ElementTree
        """
        def floatystr(fstr):
            # Strip off trailing zeros from fixed point float string
            return ('%f' % fstr).rstrip('0').rstrip('.')

        if doc_units is None:
            doc_units = 'px'
        docroot = etree.Element(svg_ns('svg'), nsmap=SVG_NS)
        width_str = floatystr(width)
        height_str = floatystr(height)
        docroot.set('width', '%s%s' % (width_str, doc_units))
        docroot.set('height', '%s%s' % (height_str, doc_units))
        docroot.set('viewbox', '0 0 %s %s' % (width_str, height_str))
        if doc_id is not None:
            docroot.set('id', doc_id)
        return etree.ElementTree(docroot)

    @classmethod
    def parse(cls, filename=None, huge_tree=True):
        """Parse an SVG file (or stdin) and return an SVGContext.

        Args:
            filename: The SVG file to parse. If this is None
                stdin will be read by default.

        Returns:
            An SVGContext
        """
        parser = etree.XMLParser(huge_tree=huge_tree)
        if filename is None:
            document = etree.parse(sys.stdin, parser=parser)
        else:
            with open(filename, 'r') as stream:
                document = etree.parse(stream, parser=parser)
        return cls(document)

    def __init__(self, document, font_size=None, x_height=None):
        """New SVG context.

        Args:
            document: An SVG ElementTree. The svg 'width' and 'height'
                attributes MUST be specified.
            font_height: CSS font-height in user units.
            ex_height: CSS x-height in user units.
        """
        self.document = document
        if hasattr(document, 'getroot'):
            # Assume ElementTree
            self.docroot = document.getroot()
        else:
            # Assume Element
            self.docroot = document
        self.current_parent = self.docroot
        self.set_precision(self._DEFAULT_PRECISION)

        if font_size is not None:
            self._UU_CONV['em'] = font_size
        if x_height is not None:
            self._UU_CONV['ex'] = x_height
        else:
            self._UU_CONV['ex'] = self._UU_CONV['em']

        # For some background on SVG coordinate systems
        # and how Inkscape deals with units:
        # http://www.w3.org/TR/SVG/coords.html
        # http://wiki.inkscape.org/wiki/index.php/Units_In_Inkscape

        # Get viewport width and height in user units
        viewport_width = self.unit_convert(self.docroot.get('width'))
        viewport_height = self.unit_convert(self.docroot.get('height'))

        # Get the viewBox to determine user units and root scale factor
        viewboxattr = self.docroot.get('viewBox')
        if viewboxattr is not None:
            p = re.compile('[,\s\t]+')
            viewbox = [float(value) for value in p.split(viewboxattr)]
        else:
            viewbox = [0, 0, viewport_width, viewport_height]
        viewbox_width = viewbox[2] - viewbox[0]
        viewbox_height = viewbox[3] - viewbox[1]

        # The viewBox can have a different size than the viewport
        # which causes the user agent to scale the SVG.
        # http://www.w3.org/TR/SVG/coords.html#ViewBoxAttribute
        # For this purpose we assume the aspect ratio is preserved
        # and that it's a degenerate case if not since it would be
        # difficult, if not impossible, to make a general scaling rule
        # for GUI value to user unit conversion.
        scale_width = viewbox_width / viewport_width
        scale_height = viewbox_height / viewport_height
        if not self.float_eq(scale_width, scale_height):
            raise Exception('viewBox aspect ratio does not match viewport.')

        self.view_width = viewbox_width
        self.view_height = viewbox_height
        self.view_scale = scale_width
        self.viewbox = viewbox

    def unit2uu(self, value, from_unit='px'):
        """Convert a string/float that specifies a value in some source unit
        (ie '3mm' or '5in') to a float value in user units.
        The result will be scaled using the viewBox/viewport ratio.
        See http://www.w3.org/TR/SVG/coords.html#ViewBoxAttribute

        Args:
            value: A numeric string value with an optional
                unit identifier suffix (ie '3mm', '10pt, '5in'), or
                a float value. If the string does not have a unit suffix
                then `src_unit` will be used.
            from_unit: A string specifying the units for the conversion.
                Default is 'px'.

        Returns:
            A float value or 0.0 if the string can't be parsed.
        """
        if isinstance(value, numbers.Number):
            return value * self._UU_CONV[from_unit] * self.view_scale
        else:
            # Assume a string...
            uu = self.unit_convert(value, from_unit=from_unit)
            return uu * self.view_scale

    def uu2unit(self, value, to_unit='px'):
        """Convert a value in user units to a destination unit.

        Args:
            value: A float value in user units.
            to_unit: Destination unit (i.e. 'in', 'mm', etc.)
                Default is 'px'.

        Returns:
            The converted value.
        """
        v = self.unit_convert(value, to_unit=to_unit)
        return v / self.view_scale

    def unit_convert(self, value, to_unit='px', from_unit='px'):
        """Convert a string that specifies a scalar value in some source unit
        (ie '3mm' or '5in') to a float value in a destination unit
        ('px', or user units, by default).
        SVG/Inkscape units and viewBoxes are confusing...
        See http://www.w3.org/TR/SVG/coords.html#ViewBoxAttribute
        and http://www.w3.org/TR/SVG/coords.html#Units
        and http://wiki.inkscape.org/wiki/index.php/Units_In_Inkscape

        Args:
            value: A string scalar with an optional unit identifier suffix.
                (ie '3mm', '10pt, '5.3in')
            to_unit: An SVG unit id of the destination unit conversion.
                Default is 'px' (user units)
            from_unit: Optional default source unit. ('px' if unspecified)

        Returns:
            A float value or 0.0 if the string can't be parsed.
        """
        retval = 0.0
        # Extract the scalar float value
        m = self._UU_FLOAT.match(value)
        if m is not None:
            retval = float(m.string[m.start():m.end()])
            m = self._UU_UNIT.search(value)
            # Source value to user-unit scale factor
            if m is not None:
                unit = m.string[m.start():m.end()]
                src2uu = self._UU_CONV.get(unit, from_unit)
            else:
                src2uu = self._UU_CONV.get(from_unit, 'px')
            # User-unit to destination value scale factor
            uu2dst = self._UU_CONV.get(to_unit, 'px')
            retval *= src2uu / uu2dst
        return retval

    def write(self, filename=None):
        """Write the SVG to a file or stdout."""
        if filename is None:
            self._write_document(sys.stdout)
        else:
            with open(filename, 'w') as stream:
                self._write_document(stream)

    def _write_document(self, stream):
        self.document.write(stream, encoding='UTF-8',
                            pretty_print=True, standalone=False)

    def set_precision(self, precision):
        """Set the output precision.

        Args:
            precision: The number of digits after the decimal point.
        """
        self._epsilon = math.pow(10.0, -precision)
        self._fmt_float = '%%.%df' % (precision,)
        self._fmt_point = '%%.%df,%%.%df' % (precision, precision)
        self._fmt_move = 'M %s' % self._fmt_point
        self._fmt_line = 'M %s L %s' % (self._fmt_point, self._fmt_point)
        self._fmt_arc = 'A %s %s %%d %%d %s' % (self._fmt_point,
                                                self._fmt_float,
                                                self._fmt_point)
        self._fmt_curve = 'C %s %s %s' % (self._fmt_point, self._fmt_point,
                                          self._fmt_point)

    def float_eq(self, a, b):
        """Compare two floats for equality in the SVG context.
        The two float are considered equal if the difference between them is
        less than epsilon. This is based on the current SVG numeric precision.

        For a discussion of floating point comparisons see:
            http://randomascii.wordpress.com/2012/02/25/comparing-floating-point-numbers-2012-edition/
        """
        return abs(a - b) < self._epsilon

    def set_default_parent(self, parent):
        """Set the current default parent (or layer) to :parent:"""
        self.current_parent = parent

    def get_node_by_id(self, node_id):
        """Find a node in the current document by id attribute.

        Args:
            node_id: The node id attribute value.

        Returns:
            A node if found otherwise None.
        """
        return get_node_by_id(self.document, node_id)

    def get_element_transform(self, node, root=None):
        """Get the combined transform of the element and it's combined parent
        transforms.
        
        Args:
            node: The element node.
            root: The document root or where to stop searching.

        Returns:
            The combined transform matrix or the identity matrix
            if none found.
        """
        matrix = self.get_parent_transform(node, root)
        transform_attr = node.get('transform')
        if transform_attr is not None and transform_attr:
            node_transform = self.parse_transform_attr(transform_attr)
            matrix = transform2d.compose_transform(matrix, node_transform)
        return matrix


    def get_parent_transform(self, node, root=None):
        """Get the combined transform of the node's parents.

        Args:
            node: The child node.
            root: The document root or where to stop searching.

        Returns:
            The parent transform matrix or the identity matrix
            if none found.
        """
        matrix = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        parent = node.getparent()
        while parent is not root:
            parent_transform_attr = parent.get('transform')
            if parent_transform_attr is not None:
                parent_matrix = self.parse_transform_attr(parent_transform_attr)
                matrix = transform2d.compose_transform(parent_matrix, matrix)
            parent = parent.getparent()
        return matrix

    def node_is_visible(self, node, check_parent=True, _recurs=False):
        """Return True if the node is visible.
        CSS visibility trumps SVG visibility attribute.

        The node is not considered visible if the `visibility` style
        is `hidden` or `collapse` or if the `display` style is `none`.
        If the `visibility` style is `inherit` or `check_parent` is True
        then the visibility is determined by the parent node.

        Args:
            node: An etree.Element node
            check_parent: Recursively check parent nodes for visibility

        Returns:
            True if the node is visible otherwise False.
        """
        if node is None:
            return _recurs
        styles = css.inline_style_to_dict(node.get('style'))
        if styles.get('display') == 'none':
            return False
        visibility = styles.get('visibility', node.get('visibility'))
        if visibility is not None:
            if visibility == 'inherit' and not check_parent:
                # Recursively determine parent visibility
                return self.node_is_visible(node.getparent(), _recurs=True)
            if visibility == 'hidden' or visibility == 'collapse':
                return False
        if check_parent:
            return self.node_is_visible(node.getparent(), _recurs=True)
        return True

    def parse_transform_attr(self, transform_attr):
        """Parse an SVG transform attribute.

        Args:
            transform_attr: A string containing the SVG transform list.

        Returns:
            A single affine transform matrix.
        """
        if (transform_attr is None or not transform_attr or
            transform_attr.isspace()):
            return transform2d.IDENTITY_MATRIX
        transform_attr = transform_attr.strip()
        transforms = self._TRANSFORM_RE.findall(transform_attr)
        matrices = []
        for transform, args in transforms:
            matrix = None
            values = [float(n) for n in args.replace(',', ' ').split()]
            num_values = len(values)
            if transform == 'translate':
                x = values[0]
                y = values[1] if num_values > 1 else 0.0
                matrix = transform2d.matrix_translate(x, y)
            if transform == 'scale':
                x = values[0]
                y = values[1] if num_values > 1 else x
                matrix = transform2d.matrix_scale(x, y)
            if transform == 'rotate':
                a = math.radians(values[0])
                cx = values[1] if num_values > 1 else 0.0
                cy = values[2] if num_values > 2 else 0.0
                matrix = transform2d.matrix_rotate(a, (cx, cy))
            if transform == 'skewX':
                a = math.radians(values[0])
                matrix = transform2d.matrix_skew_x(a)
            if transform == 'skewY':
                a = math.radians(values[0])
                matrix = transform2d.matrix_skew_y(a)
            if transform == 'matrix':
                matrix = ((values[0], values[2], values[4]),
                          (values[1], values[3], values[5]))
            if matrix is not None:
                matrices.append(matrix)

        # Compose all the tranforms into one matrix
        result_matrix = transform2d.IDENTITY_MATRIX
        for matrix in matrices:
            result_matrix = transform2d.compose_transform(result_matrix, matrix)

        return result_matrix

    def scale_inline_style(self, inline_style):
        """For any inline style attribute name that ends with
        'width', 'height', or 'size'
        scale the numeric value with an optional unit id suffix
        by converting it to user units with no unit id.
        """
        style_attrs = css.inline_style_to_dict(inline_style)
        for attr, value in style_attrs.viewitems():
            if attr.endswith(('width', 'height', 'size')):
                # Automatically convert unit values
                style_attrs[attr] = self.unit2uu(value)
        return css.dict_to_inline_style(style_attrs)

    def styles_from_templates(self, style_templates, default_map,
                              template_map=None):
        """Populate a dictionary of styles given a dictionary of templates and
        mappings.
        If a template key string ends with 'width', 'height', or 'size'
        it is assumed that the value is a numeric value with an optional
        unit id suffix and it will be automatically converted to user units
        with no unit id.

        Args:
            style_templates: A dictionary of style names to
                inline style template strings.
            default_map: A dictionary of template keys to
                default values. This must contain all template identifiers.
            template_map: A dictionary of template keys to
                values that override the defaults. Default is None.

        Returns:
            A dictionary of inline styles.
        """
        # Create a template mapping that fills in missing values
        # from the default map.
        mapping = {}
#         for key in default_map.iterkeys():
        for key in default_map:
            value = None
            if template_map is not None:
                value = template_map.get(key)
            if value is None:
                value = default_map[key]
            if value is not None:
                # If the value is a numeric type then it is assumed
                # to already be in user units...
                if (key.endswith(('width', 'height', 'size'))
                        and not isinstance(value, numbers.Number)):
                    # Automatically convert unit values
                    mapping[key] = self.unit2uu(value)
                else:
                    mapping[key] = value
        styles = {}
        for name, template_str in style_templates.iteritems():
            template = string.Template(template_str)
            styles[name] = template.substitute(mapping)
        return styles

    def node_is_group(self, node):
        """Return True if the node is an SVG group."""
        return node.tag == svg_ns('g') or node.tag == 'g'

    def create_rect(self, position, width, height, style=None, parent=None):
        """Create an SVG rect element."""
        if parent is None:
            parent = self.current_parent
        attrs = {'x': str(self._scale(position[0])),
                 'y': str(self._scale(position[1])),
                 'width': str(self._scale(width)),
                 'height': str(self._scale(height))}
        if style:
            attrs['style'] = style
        return etree.SubElement(parent, svg_ns('rect'), attrs)

    def create_circle(self, center, radius, style=None, parent=None):
        """Create an SVG circle element."""
        if parent is None:
            parent = self.current_parent
        attrs = {'r': str(self._scale(radius)),
                 'cx': str(self._scale(center[0])),
                 'cy': str(self._scale(center[1]))}
        if style:
            attrs['style'] = style
        return etree.SubElement(parent, svg_ns('circle'), attrs)

    def create_ellipse(self, center, rx, ry, angle, style=None, parent=None):
        """Create an SVG ellipse."""
        # See http://www.w3.org/TR/SVG/implnote.html#ArcImplementationNotes
        # for converting center parameterization to SVG arc
        # Normalize angle first:
        angle = angle - (2 * math.pi) * math.floor(angle / (2 * math.pi))
        x1 = rx * math.cos(angle) + center.x
        y1 = rx * math.sin(angle) + center.y
        x2 = rx * math.cos(angle + math.pi) + center.x
        y2 = rx * math.sin(angle + math.pi) + center.y
        m = self._fmt_move % (self._scale(x1), self._scale(y1))
        a1 = self._fmt_arc % (self._scale(rx), self._scale(ry),
                              math.degrees(angle), 0, 1,
                              self._scale(x2), self._scale(y2))
        a2 = self._fmt_arc % (self._scale(rx), self._scale(ry),
                              math.degrees(angle), 0, 1,
                              self._scale(x1),
                              self._scale(y1))
        attrs = {'d': m + ' ' + a1 + ' ' + a2, }
        return self.create_path(attrs, style, parent)

    def create_line(self, p1, p2, style=None, parent=None, attrs=None):
        """Create an SVG path consisting of one line segment."""
        line_path = self._fmt_line % (self._scale(p1[0]), self._scale(p1[1]),
                                      self._scale(p2[0]), self._scale(p2[1]))
        if attrs is None:
            attrs = {}
        attrs['d'] = line_path
        return self.create_path(attrs, style, parent)

    def create_circular_arc(self, startp, endp, radius, sweep_flag,
                            style=None, parent=None, attrs=None):
        """Create an SVG circular arc."""
        m = self._fmt_move % (self._scale(startp[0]),
                              self._scale(startp[1]))
        a = self._fmt_arc % (self._scale(radius), self._scale(radius),
                             0, 0, sweep_flag,
                             self._scale(endp[0]), self._scale(endp[1]))
        if attrs is None:
            attrs = {}
        attrs['d'] = m + ' ' + a
        return self.create_path(attrs, style, parent)

    def create_curve(self, startp, cp1=None, cp2=None, p2=None,
                            style=None, parent=None, attrs=None):
        """Create an SVG cubic bezier curve.

        Args:
            startp: The start point of the curve or an indexable
                collection of four control points.
            style: A CSS style string.
            parent: The parent element (or Inkscape layer).
            attrs: Dictionary of SVG element attributes.

        Returns:
            An SVG path Element node.
        """
        d = []
        if cp1 is None:
            p1, cp1, cp2, p2 = startp
        else:
            p1 = startp
        d.append(self._fmt_move % (self._scale(p1[0]),
                                   self._scale(p1[1])))
        d.append(self._format_curve(cp1, cp2, p2))
        if attrs is None:
            attrs = {}
        attrs['d'] = ' '.join(d)
        return self.create_path(attrs, style, parent)

    def _format_curve(self, cp1=None, cp2=None, p2=None):
        return self._fmt_curve % (self._scale(cp1[0]), self._scale(cp1[1]),
                                  self._scale(cp2[0]), self._scale(cp2[1]),
                                  self._scale(p2[0]), self._scale(p2[1]))

    def create_polygon(self, vertices, close_polygon=True, close_path=False,
                       style=None, parent=None, attrs=None):
        """Create an SVG path describing a polygon.

        Args:
            vertices: An iterable collection of 2D polygon vertices.
                A vertice being a tuple containing x,y coordicates.
            close_polygon: Close the polygon if it isn't already.
                Default is True.
            close_path: Close and join the the path ends by
                appending 'Z' to the end of the path ('d') attribute.
                Default is False.
            style: A CSS style string.
            parent: The parent element (or Inkscape layer).
            attrs: Dictionary of SVG element attributes.

        Returns:
            An SVG path Element node, or None if the list of vertices is empty.
        """
        if not vertices:
            return None
        d = ['M', self._fmt_point % (self._scale(vertices[0][0]),
                                      self._scale(vertices[0][1])), 'L']
        for p in vertices[1:]:
            d.append(self._fmt_point % (self._scale(p[0]),
                                        self._scale(p[1])))
        if close_polygon and vertices[0] != vertices[-1]:
            d.append(self._fmt_point % (self._scale(vertices[0][0]),
                                        self._scale(vertices[0][1])))
        if close_path:
            d.append('Z')
        if attrs is None:
            attrs = {}
        attrs['d'] = ' '.join(d)
        return self.create_path(attrs, style, parent)

    def create_polypath(self, path, close_path=False, style=None,
                        parent=None, attrs=None):
        """Create an SVG path from a sequence of line and arc segments.

        Args:
            path: An iterable sequence of line, circular arc, or cubic
                Bezier curve  segments.
                A line segment is a 2-tuple containing the endpoints.
                An arc segment is a 5-tuple containing the start point,
                end point, radius, angle, and center, respectively. The
                arc center is ignored.
                A cubic bezier segment is a 4-tuple containing the first
                endpoint, the first control point, the second control point,
                and the second endpoint.
            close_path: Close and join the the path ends by
                appending 'Z' to the end of the path ('d') attribute.
                Default is False.
            style: A CSS style string.
            parent: The parent element (i.e. Inkscape layer).
            attrs: Dictionary of SVG element attributes.

        Returns:
            An SVG path Element node, or None if the path is empty.
        """
        if not path:
            return None
        p1 = path[0][0]
        d = ['M', self._fmt_point % (self._scale(p1[0]), self._scale(p1[1]))]
        for segment in path:
            if len(segment) == 2:
                # Assume this is a line segment with two endpoints:
                # ((x1, y1), (x2, y2))
                p2 = segment[1]
                d.append('L')
                d.append(self._fmt_point % (self._scale(p2[0]),
                                            self._scale(p2[1])))
            elif len(segment) == 4:
                # Assume this is a cubic Bezier:
                # ((x1, y1), (cx1, cx1), (cx2, cx2), (x2, y2))
                cp1 = segment[1]
                cp2 = segment[2]
                p2 = segment[3]
                d.append(self._format_curve(cp1, cp2, p2))
            elif len(segment) == 5:
                # Assume this is an arc segment:
                # ((x1, y1), (x2, y2), radius, angle, center)
                p2 = segment[1]
                radius = segment[2]
                angle = segment[3]
                sweep_flag = 0 if angle < 0 else 1
                arc = self._fmt_arc % (self._scale(radius), self._scale(radius),
                                       0, 0, sweep_flag,
                                       self._scale(p2[0]), self._scale(p2[1]))
                d.append(arc)
        if close_path:
            d.append('Z')
        if attrs is None:
            attrs = {}
        attrs['d'] = ' '.join(d)
        return self.create_path(attrs, style, parent)

    def create_simple_marker(self, marker_id, d, style, transform,
                             replace=False):
        """Create an SVG line end marker glyph.

        The glyph Element is placed under the document root.
        """
        defs = self.docroot.find(svg_ns('defs'))
        if defs is None:
            defs = etree.SubElement(self.docroot, svg_ns('defs'))
        elif replace:
            # If a marker with the same id already exists
            # then remove it first.
            node = defs.find('*[@id="%s"]' % marker_id)
            if node is not None:
                node.getparent().remove(node)
        marker = etree.SubElement(defs, svg_ns('marker'),
                        {'id': marker_id, 'orient': 'auto', 'refX':  '0.0',
                         'refY': '0.0', 'style': 'overflow:visible', })
        etree.SubElement(marker, svg_ns('path'),
                        { 'd': d, 'style': style, 'transform': transform, })
        return marker

    def create_path(self, attrs, style=None, parent=None):
        """Create an SVG path element."""
        if parent is None:
            parent = self.current_parent
        if style is not None:
            attrs['style'] = style
        return etree.SubElement(parent, svg_ns('path'), attrs)

    def create_text(self, text, x, y, line_height=None,
                    style=None, parent=None):
        """Create a text block.
        """
        if parent is None:
            parent = self.current_parent
        attrs = {'x': str(self._scale(x)), 'y': str(self._scale(y)),
                 xml_ns('space'): 'preserve',
                 'style': style
                 }
        text_elem = etree.SubElement(parent, svg_ns('text'), attrs)
        if isinstance(text, basestring):
            self._create_text_line(text, x, y, text_elem)
        else:
            for text_line in text:
                self._create_text_line(text_line, x, y, text_elem)
                y += line_height
        return text_elem

    def _create_text_line(self, text, x, y, parent):
        attrs = {'x': str(self._scale(x)), 'y': str(self._scale(y)), }
        tspan_elem = etree.SubElement(parent, svg_ns('tspan'), attrs)
        tspan_elem.text = text
        return tspan_elem

    def _scale(self, n):
        # TODO: apply viewport scaling
        # noop for now
        return n

#     def _rotate_point(self, x, y, angle):
#         """Rotate point by angle amount around origin point."""
#         x = x * math.cos(angle) - y * math.sin(angle)
#         y = y * math.cos(angle) + x * math.sin(angle)
#         return (x, y)

def path_tokenizer(path_data):
    """Tokenize SVG path data.

    A generator that yields tokens from path data.
    This will yield a tuple containing a
    command token or a numeric parameter token
    followed by a boolean flag that is True if the token
    is a command and False if the token is a numeric parameter.

    Yields:
        A 2-tuple with token and token type hint.
    """
    #--------------------------------------------------------------------------
    # Thanks to Peter Stangl for this.
    # It is significantly faster than using regexp.
    # https://codereview.stackexchange.com/users/71285/peter-stangl
    #
    # See:
    #     https://codereview.stackexchange.com/questions/28502/svg-path-parsing
    #     https://www.w3.org/TR/SVG/paths.html#PathDataBNF
    #--------------------------------------------------------------------------
    DIGIT_EXP = '0123456789eE'
    COMMA_WSP = ', \t\n\r\f\v'
    DRAWTO_COMMAND = 'MmZzLlHhVvCcSsQqTtAa'
    SIGN = '+-'
    EXPONENT = 'eE'
    in_float = False
    entity = ''
    for char in path_data:
        if char in DIGIT_EXP:
            entity += char
        elif char in COMMA_WSP and entity:
            yield (entity, False) # Number parameter
            in_float = False
            entity = ''
        elif char in DRAWTO_COMMAND:
            if entity:
                yield (entity, False) # Number parameter
                in_float = False
                entity = ''
            yield (char, True) # Yield a command
        elif char == '.':
            if in_float:
                yield (entity, False) # Number parameter
                entity = '.'
            else:
                entity += '.'
                in_float = True
        elif char in SIGN:
            if entity and entity[-1] not in EXPONENT:
                yield (entity, False) # Number parameter
                in_float = False
                entity = char
            else:
                entity += char
    if entity:
        yield (entity, False) # Number parameter


"""
    This parser metadata structure is shamelessly borrowed from
    Aaron Spike's simplepath parser with minor modifications.

    {path-command:
    [
    output-command, # Canonical command
    num-params, # Expected number of parameters
    [casts, ...], # float, int
    [coord-axis, ...] # 0 == x, 1 == y, -1 == not a coordinate param
    ]}
"""
_PATHDEFS = {
    'M': ['M', 2, [float, float], [0, 1]],
    'L': ['L', 2, [float, float], [0, 1]],
    'H': ['L', 1, [float], [0, ]],
    'V': ['L', 1, [float], [1, ]],
    'C': ['C', 6, [float, float, float, float, float, float],
          [0, 1, 0, 1, 0, 1]],
    'S': ['C', 4, [float, float, float, float], [0, 1, 0, 1]],
    'Q': ['Q', 4, [float, float, float, float], [0, 1, 0, 1]],
    'T': ['Q', 2, [float, float], [0, 1]],
    'A': ['A', 7, [float, float, float, int, int, float, float],
          [-1, -1, -1, -1, -1, 0, 1]],
    'Z': ['L', 0, [], []]}

def parse_path(path_data):
    """Parse an SVG path definition string.
    Converts relative values to absolute and
    shorthand commands to canonical (ie. H to L, S to C, etc.)
    Terminating Z (or z) converts to L.

    If path syntax errors are encountered, parsing will simply stop.
    No exceptions are raised. This is by design so that parsing
    is relatively forgiving of input.

    Implemented as a generator so that memory usage can be minimized
    for very long paths.

    Args:
        path_def: The 'd' attribute value of a SVG path element.

    Yields:
        A path component 2-tuple of the form (cmd, params).
    """
    # Current command context
    current_cmd = None
    # Current path command definition
    pathdef = _PATHDEFS['M']
    # Start of sub-path
    moveto = (0.0, 0.0)
    # Current drawing position
    pen = (0.0, 0.0)
    # Last control point for curves
    last_control = pen
    # True if the command is relative
    cmd_is_relative = False
    # True if the parser expects a command
    expecting_command = True
    # Current accumulated parameters
    params = []

    tokenizer = path_tokenizer(path_data)
    pushed_token = None

    while True:
        if pushed_token is not None:
            token, is_command = pushed_token
            pushed_token = None
        else:
            try:
                token, is_command = tokenizer.next()
            except StopIteration:
                break
        if expecting_command:
            if current_cmd == None and token.upper() != 'M':
                break
            if is_command:
                cmd_is_relative = token.islower()
                cmd = token.upper()
                pathdef = _PATHDEFS[cmd]
                current_cmd = cmd
                if current_cmd == 'Z':
                    # Push back an empty token since this has no parameters
                    pushed_token = ('', False)
            else:
                # In implicit command
                if current_cmd == 'M':
                    # Any subsequent parameters are for an implicit LineTo
                    current_cmd = 'L'
                    pathdef = _PATHDEFS[current_cmd]
                # Push back token for parameter accumulation on next pass
                pushed_token = (token, is_command)
            expecting_command = False
        else:
            if is_command:
                # Bail if number of parameters doesn't match command
                break
            # Accumulate parameters for the current command
            nparams = len(params)
            if nparams < pathdef[1]:
                cast = pathdef[2][nparams]
                value = cast(token)
                if cmd_is_relative:
                    axis = pathdef[3][nparams]
                    if axis >= 0:
                        # Make relative value absolute
                        value += pen[axis]
                params.append(value)
                nparams += 1
            if nparams == pathdef[1]:
                if current_cmd == 'M':
                    moveto = (params[0], params[1])
                elif current_cmd == 'Z':
                    params.extend(moveto)
                    pushed_token = None
                elif current_cmd == 'H':
                    params.append(pen[1])
                elif current_cmd == 'V':
                    params.insert(0, pen[1])
                elif current_cmd in ('S', 'T'):
                    params.insert(0, pen[1] + (pen[1] - last_control[1]))
                    params.insert(0, pen[0] + (pen[0] - last_control[0]))
                if current_cmd in ('C', 'Q'):
                    last_control = (params[-4], params[-3])
                else:
                    last_control = pen
                output_cmd = pathdef[0]
                yield (output_cmd, params)
                # Update the drawing position to the last end point.
                pen = (params[-2], params[-1])
                params = []
                expecting_command = True


def explode_path(path_data):
    """Break the path at node points into component segments.

    Args:
        path_def: The 'd' attribute value of a SVG path element.
        
    Returns:
        A list of path 'd' attribute values.
    """
    dlist = []
    p1 = None
    for cmd, params in parse_path(path_data):
        if cmd == 'M':
            p1 = (params[-2], params[-1])
            continue
        p2 = (params[-2], params[-1])
        if p1 is not None:
            paramstr = ' '.join([str(param) for param in params])
            d = 'M %f %f %s %s' % (p1[0], p1[1], cmd, paramstr)
            dlist.append(d)
        p1 = p2
    return dlist

def create_svg_document(width, height, doc_units='px', doc_id=None):
    """Create a minimal SVG document tree.

    The svg element `viewbox` attribute will maintain the size and
    attribute ratio as specified by width and height.

    Args:
        width: The width of the document in user units.
        height: The height of the document in user units.
        doc_units: The user unit type (i.e. 'in', 'mm', 'pt', 'em', etc.)
            By default this will be 'px'.
        doc_id: The id attribute of the enclosing svg element.
            If None (default) then a random id will be generated.

    Returns:
        An lxml.etree.ElementTree
    """
    def floatystr(value):
        # Strip off trailing zeros from fixed point float string
        # This is similar to the 'g' format but wont display scientific
        # notation for big numbers.
        return ('%f' % float(value)).rstrip('0').rstrip('.')

    docroot = etree.Element(svg_ns('svg'), nsmap=SVG_NS)
    width_str = floatystr(width)
    height_str = floatystr(height)
    docroot.set('width', '%s%s' % (width_str, doc_units))
    docroot.set('height', '%s%s' % (height_str, doc_units))
    docroot.set('viewbox', '0 0 %s %s' % (width_str, height_str))
    if doc_id is None:
        doc_id = random_id()
    docroot.set('id', doc_id)
    return etree.ElementTree(docroot)


def random_id(prefix='_svg', rootnode=None):
    """Create a random XML id attribute value.

    Args:
        prefix: The prefix prepended to a random number.
            Default is '_svg'.
        rootnode: The root element to search for id name collisions.
            Default is None in which case no search will be performed.

    Returns:
        A random id string that has a fairly low chance of collision
        with previously generated ids.
    """
    id_attr = '%s%d' % (prefix, random.randint(1, 2 ** 31))
    if rootnode is not None:
        while get_node_by_id(rootnode, id) is not None:
            id_attr = '%s%d' % (prefix, random.randint(1, 2 ** 31))
    return id_attr

def get_node_by_id(rootnode, node_id):
    """Find a node in the current document by id attribute.

    Args:
        rootnode: The root element to search.
        node_id: The node id attribute value.

    Returns:
        A node if found otherwise None.
    """
    return rootnode.find('//*[@id="%s"]' % node_id)

def transform_attr(matrix):
    return 'matrix(%f,%f,%f,%f,%f,%f)' % (matrix[0][0], matrix[1][0],
                                          matrix[0][1], matrix[1][1],
                                          matrix[0][2], matrix[1][2])
