#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
A simple library for SVG output - but more Inkscape-centric.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import re
import logging
logger = logging.getLogger(__name__)

from lxml import etree

import geom
from geom import transform2d

from svg import svg
from svg.svg import svg_ns, _add_ns

# Dictionary of XML namespaces used in Inkscape documents
INKSCAPE_NS = {
#     None: u'http://www.w3.org/2000/svg',
#     u'svg': u'http://www.w3.org/2000/svg',
#     u'xlink': u'http://www.w3.org/1999/xlink',
#     u'xml': u'http://www.w3.org/XML/1998/namespace',
#     u'cc': u'http://creativecommons.org/ns#',
#     u'ccOLD': u'http://web.resource.org/cc/',
#     u'dc': u'http://purl.org/dc/elements/1.1/',
#     u'rdf': u'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    u'inkscape': u'http://www.inkscape.org/namespaces/inkscape',
    u'sodipodi': u'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd',
}
# Add the standard SVG namespaces
INKSCAPE_NS.update(svg.SVG_NS)

# Vendor specific namespace (in this case us)
UTLCO_NS = {
    u'utlco': u'http://www.utlco.com/namespaces/utlco',
}

def inkscape_ns(tag):
    """Prepend the `inkscape` namespace to an element tag."""
    return _add_ns(tag, INKSCAPE_NS, 'inkscape')

def sodipodi_ns(tag):
    """Prepend the `sodipodi` namespace to an element tag."""
    return _add_ns(tag, INKSCAPE_NS, 'sodipodi')

def utlco_ns(tag):
    """Prepend the `utlco` namespace to an element tag"""
    return _add_ns(tag, UTLCO_NS, 'utlco')

class InkscapeSVGContext(svg.SVGContext):
    """"""
    _DEFAULT_SHAPES = ('path', 'rect', 'line', 'circle',
                       'ellipse', 'polyline', 'polygon')
    _DEFAULT_DOC_UNITS = 'px'


    def __init__(self, document, *args, **kwargs):
        """"""
        super(InkscapeSVGContext, self).__init__(document, *args, **kwargs)
        #: Inkscape document name
        self.doc_name = self.docroot.get('sodipodi:docname', 'untitled.svg')
        # The Inkscape doc unit overrides the implicit SVG unit
        basedoc = self.find('//sodipodi:namedview')
        basedoc_units = basedoc.get('units', self._DEFAULT_DOC_UNITS)
        #: Inkscape GUI document units
        self.doc_units = basedoc.get(inkscape_ns('document-units'),
                                     basedoc_units)
        #: Document clipping rectangle
        self.cliprect = geom.Box((0, 0), self.get_document_size())
        # Current Inkscape layer
        self._current_layer_id = basedoc.get(inkscape_ns('current-layer'))
        layer = self.get_selected_layer()
        if layer is None:
            layer = self.docroot
        self.set_default_parent(layer)

    def get_document_size(self):
        """Return width and height of document in user units as a tuple (W, H).
        """
        return (self.view_width, self.view_height)

    def margin_cliprect(self, mtop, *args):
        """
        Create a clipping rectangle based on document bounds with
        the specified margins.
        Margin argument order follows CSS margin property rules.

        Args:
            mtop: Top margin (user units)
            mright: Right margin (user units)
            mbottom: Bottom margin (user units)
            mleft: Left margin (user units)

        Returns:
            A geom.Box clipping rectangle
        """
        doc_size = self.get_document_size()
        mright = mtop
        mbottom = mtop
        mleft = mtop
        if len(args) > 0:
            mright = args[0]
            mleft = args[0]
        if len(args) > 1:
            mbottom = args[1]
        if len(args) > 2:
            mleft = args[2]
        return geom.Box((mleft, mbottom),
                        (doc_size[0] - mright, doc_size[1] - mtop))

    def get_document_name(self):
        """Return the name of this document. Default is 'untitled'."""
        self.doc_name

    def get_document_units(self):
        """Return the Inkscape document unit string ('in', 'mm', etc.).
        This is the document unit used for the UI (dialogs etc.).
        It might not be the same as the document user unit.
        """
        return self.doc_units

    def get_selected_layer(self):
        """Get the currently selected Inkscape layer element.

        Returns:
            The currently selected layer element or None
            if no layers are selected.
        """
        if self._current_layer_id is not None:
            return self.get_node_by_id(self._current_layer_id)
        return None

    def find_layer(self, layer_name):
        """Find an Inkscape layer by Inkscape layer name.

        If there is more than one layer by that name then just the
        first one will be returned.

        :param layer_name: The Inkscape layer name to find.
        :return: The layer Element node or None.
        """
        return self.find('//svg:g[@inkscape:label="%s"]' % layer_name)

#    def clear_layer(self, layer_name):
#        """Delete the contents of the specified layer.
#        Does nothing if the layer doesn't exist.
#        """
#        layer = self.find_layer(layer_name)
#        if layer is not None:
#            del layer[:]

    def create_layer(self, name, opacity=None, clear=True,
                     incr_suffix=False, flipy=False, tag=None):
        """Create an Inkscape layer or return an existing layer.

        Args:
            name: The name of the layer to create.
            opacity: Layer opacity (0.0 to 1.0).
            clear: If a layer of the same name already exists then
                erase it first if True otherwise just return it.
                Default is True.
            incr_suffix: If a layer of the same name already exists and
                it is non-empty then add an auto-incrementing numeric suffix
                to the name (overrides *clear*).
            flipy: Add transform to flip Y axis.
            tag (str): A layer tag added as an extended attribute.
                Uses `utlco` namespace. This can be used to tag layers
                with a custom label.

        Returns:
            A new layer or an existing layer of the same name.
        """
        layer_name = name
        layer = self.find_layer(name)
        if layer is not None and incr_suffix and len(layer) > 0:
            suffix_n = 0
            while layer is not None and len(layer) > 0:
                layer_name = '%s_%02d' % (name, suffix_n)
                suffix_n += 1
                layer = self.find_layer(layer_name)
        if layer is None:
            layer_attrs = {inkscape_ns('groupmode'): 'layer',
                           inkscape_ns('label'): layer_name}
            if tag is not None:
                layer_attrs[utlco_ns('tag')] = tag
            if opacity is not None:
                opacity = min(max(opacity, 0.0), 1.0)
                layer_attrs['style'] = 'opacity: %.2f;' % opacity
            if flipy:
                transfrm = 'translate(0, %g) scale(1, -1)' % self.view_height
                layer_attrs['transform'] = transfrm
            layer = etree.SubElement(self.docroot, 'g', layer_attrs)
        elif clear:
            # Remove subelements
            del layer[:]
#             if 'transform' in layer.attrib:
#                 del layer.attrib['transform']
        return layer

#     def _find_auto_incr_layer_name(self, name, force_new=False):
#         """
#         """
#         layer_name = name
#         layer = self.find_layer(layer_name)
#         suffix_n = 0
#         while layer is not None and (len(layer) > 0 or force_new):
#             layer_name = '%s %02d' % (name, suffix_n)
#             suffix_n += 1
#             layer = self.find_layer(layer_name)
#         return layer_name
#
#     def duplicate_layer(self, layer, new_name=None):
#         """Create a copy of an Inkscape layer and all of its sub-elements.
#
#         Args:
#             layer: The layer to copy
#             new_name: Name of the copy.
#                 By default the name will be the name of the source layer
#                 followed by an auto-incremented suffix.
#
#         Returns:
#             A copy of the specified layer.
#         """
#         raise NotImplementedError()
#         src_name = self.get_layer_name(layer)
#         if new_name is None:
#             new_name = src_name


    def set_layer_name(self, layer, name):
        """Rename an Inkscape layer.
        """
        layer.set(inkscape_ns('label'), name)

    def get_layer_name(self, layer):
        """Return the name of the Inkscape layer.
        """
        return layer.get(inkscape_ns('label'))

    def get_parent_layer(self, node):
        """Return the layer that the node resides in.
        Returns None if the node is not in a layer.
        """
        # TODO: it's probably better/faster to recursively climb
        # the parent chain until docroot or layer is found.
        # This assumes that Inkscape still doesn't support sub-layers
        layers = self.document.xpath('//svg:g[@inkscape:groupmode="layer"]',
                                     namespaces=INKSCAPE_NS)
        for layer in layers:
            if node in layer.iter():
                return layer
        return None

    def layer_is_locked(self, layer):
        """
        Returns:
            True if the layer is locked, otherwise False.
        """
        val = layer.get(sodipodi_ns('insensitive'))
        return val is not None and val.lower() == 'true'

    def find(self, path):
        """Find an element in the current document.

        Args:
            path: XPath path.

        Returns:
            The first matching element or None if not found.
        """
        try:
            node = self.document.xpath(path, namespaces=INKSCAPE_NS)[0]
        except IndexError:
            node = None
        return node

    def get_visible_layers(self):
        """Get a list of visible layers
        """
        layers = []
        for node in self.docroot:
            if self.is_layer(node) and self.node_is_visible(node):
                layers.append(node)
        return layers

    def get_layer_elements(self, layer):
        """Get document elements by layer.

        Returns all the visible child elements of the given layer.

        Args:
            layer: The layer root element.

        Returns:
            A (possibly empty) list of visible elements.
        """
        elements = []
        if self.node_is_visible(layer):
            for node in layer:
                if self.node_is_visible(node, check_parent=False):
                    elements.append(node)
        return elements

    def is_layer(self, node):
        """Determine if the element is an Inkscape layer node.
        """
        if self.node_is_group(node):
            layer_name = self.get_layer_name(node)
            return layer_name is not None and layer_name
        return False

    def get_shape_elements(self, rootnode,
                        shapetags=_DEFAULT_SHAPES,
                        parent_transform=None, skip_layers=None,
                        accumulate_transform=True):
        """
        Traverse a tree of SVG nodes and flatten it to a list of
        tuples containing an SVG shape element and its accumulated transform.

        This does a depth-first traversal of <g> and <use> elements.

        Hidden elements are ignored.

        Args:
            rootnode: The root of the node tree to traverse and flatten.
                This can be the document root, a layer,
                or simply a list of element nodes.
            shapetags: List of shape element tags that can be fetched.
                Default is ('path', 'rect', 'line', 'circle',
                'ellipse', 'polyline', 'polygon').
                Anything else is ignored.
            parent_transform: Transform matrix to add to each node's
                transforms. If None the node's parent transform is used.
            skip_layers: A list of layer names (as regexes) to ignore
            accumulate_transform: Apply parent transform(s) to element node
                if True. Default is True.

        Returns:
            A possibly empty list of 2-tuples consisting of
            SVG element and accumulated transform.
        """
        if etree.iselement(rootnode):
            if not self.node_is_visible(rootnode):
                return []
            check_parent = False
        else:
            # rootnode will be a list of possibly non-sibling element nodes
            # so the parent's visibility should be checked for each node.
            check_parent = True
        nodes = []
        for node in rootnode:
            nodes.extend(self._get_shape_nodes_recurs(node, shapetags,
                                                      parent_transform,
                                                      check_parent,
                                                      skip_layers,
                                                      accumulate_transform))
        return nodes

    def _get_shape_nodes_recurs(self, node, shapetags, parent_transform,
                                check_parent, skip_layers,
                                accumulate_transform):
        """Recursively traverse an SVG node tree and flatten it to a list of
        tuples containing an SVG shape element and its accumulated transform.

        This does a depth-first traversal of <g> and <use> elements.
        Anything besides paths, rectangles, circles, ellipses, lines, polygons,
        and polylines are ignored.

        Hidden elements are ignored.

        Args:
            node: The root of the node tree to traverse and flatten.
            shapetags: List of shape element tags that can be fetched.
            parent_transform: Transform matrix to add to each node's transforms.
            check_parent: Check parent visibility
            skip_layers: A list of layer names (as regexes) to ignore
            accumulate_transform: Apply parent transform(s) to element node
                if True.

        Returns:
            A possibly empty list of 2-tuples consisting of
            SVG element and transform.
        """
        if not self.node_is_visible(node, check_parent=check_parent):
            return []
        if parent_transform is None:
            parent_transform = self.get_parent_transform(node)
        nodelist = []
        # first apply the current transform matrix to this node's tranform
        node_transform = self.parse_transform_attr(node.get('transform'))
        if accumulate_transform:
            node_transform = transform2d.compose_transform(parent_transform,
                                                           node_transform)
        if self.node_is_group(node):
            if self.is_layer(node) and skip_layers is not None and skip_layers:
                layer_name = self.get_layer_name(node)
#                logger.debug('layer: %s', layer_name)
                for skip_layer in skip_layers:
                    if re.match(skip_layer, layer_name) is not None:
#                        logger.debug('skipping layer: %s', layer_name)
                        return []
            # Recursively traverse group children
            for child_node in node:
                subnodes = self._get_shape_nodes_recurs(child_node, shapetags,
                                                        node_transform,
                                                        False, skip_layers,
                                                        accumulate_transform)
                nodelist.extend(subnodes)
        elif node.tag == svg_ns('use') or node.tag == 'use':
            # A <use> element refers to another SVG element via an
            # xlink:href="#id" attribute.
            refid = node.get(svg.xlink_ns('href'))
            if refid:
                # [1:] to ignore leading '#' in reference
                refnode = self.get_node_by_id(refid[1:])
                # TODO: Can the referred node not be visible?
                if refnode is not None: # and self.node_is_visible(refnode):
                    # Apply explicit x,y translation transform
                    x = float(node.get('x', '0'))
                    y = float(node.get('y', '0'))
                    if x != 0 or y != 0:
                        translation = transform2d.matrix_translate(x, y)
                        node_transform = transform2d.compose_transform(
                                            node_transform, translation)
                    subnodes = self._get_shape_nodes_recurs(refnode, shapetags,
                                                            node_transform,
                                                            False, skip_layers,
                                                            accumulate_transform)
                    nodelist.extend(subnodes)
        elif svg.strip_ns(node.tag) in shapetags:
            nodelist.append((node, node_transform))
        return nodelist


def create_inkscape_document(width, height, doc_units='px', doc_id=None,
                             doc_name=None,
                             layer_name=None, layer_id='defaultlayer'):
    """Create a minimal Inkscape-compatible SVG document.

    Args:
        width: The width of the document in user units.
        height: The height of the document in user units.
        doc_units: The user unit type (i.e. 'in', 'mm', 'pt', 'em', etc.)
            By default this will be 'px'.
        doc_id: The id attribute of the enclosing svg element.
            If None (default) then a random id will be generated.
        doc_name: The name of the document (i.e. 'MyDrawing.svg').
        layer_name: Display name of default layer.
            By default no default layer will be created.
        layer_id: Id attribute value of default layer.
            Default id is 'defaultlayer'.

    Returns:
        An lxml.etree.ElementTree
    """
    document = svg.create_svg_document(width, height, doc_units, doc_id)
    docroot = document.getroot()
    # Add Inkscape-specific elements...
    if doc_name is not None and doc_name:
        docroot.set(sodipodi_ns('docname'), doc_name)
    namedview = etree.SubElement(docroot, sodipodi_ns('namedview'),
                                 id='namedview')
    namedview.set(inkscape_ns('document-units'), doc_units)
    if layer_name is not None and layer_name:
        layer = etree.SubElement(docroot, svg_ns('g'), id=layer_id)
        layer.set(inkscape_ns('groupmode'), 'layer')
        layer.set(inkscape_ns('label'), layer_name)
        namedview.set(inkscape_ns('current-layer'), layer_id)
    return document

