#-----------------------------------------------------------------------------
# Copyright 2012-2016 Claude Zervas
# email: claude@utlco.com
#-----------------------------------------------------------------------------
"""
Simple planar graph data structure.
"""
# Python 3 compatibility boilerplate
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from future_builtins import *

import random
# import logging

from .point import P
from .line import Line
from .util import normalize_angle
from . import polygon

# logger = logging.getLogger(__name__)

class GraphNode(list):
    """Graph node.

    A node has a vertex and a list of outgoing nodes that
    define the outgoing edges that connect to other nodes
    in the graph.
    """
    def __init__(self, vertex, edge_nodes=None):
        """Graph node.

        Args:
            vertex: The vertex associated with this node.
        """
        if edge_nodes != None:
#             super(GraphNode, self).__init__(edge_nodes)
            for node in edge_nodes:
                self.append(node)
        self.vertex = vertex

    def degree(self):
        """Number of incident graph edges.
        I.e. number of edges that share this node's vertex.

        See:
            http://mathworld.wolfram.com/VertexOrder.html
        """
        return len(self)

    def add_edge_node(self, edge_node):
        """Add an outgoing edge node.
        """
        self.append(edge_node)

#     def connected_nodes(self):
#         """A list of nodes that are connected to this one via common edges.
#         """
#         return self

    def sort_edges(self):
        """Sort outgoing edges in CCW order.
        """
        ref_point = P(self.vertex.x + 1, self.vertex.y)
#         ref_point = node[0].vertex
        def sortkey(edge_node):
            ccw_angle = self.vertex.angle2(ref_point, edge_node.vertex)
            return normalize_angle(ccw_angle)
        self.sort(key=sortkey)

    def ccw_edge_node(self, ref_node, skip_spikes=True):
        """The most CCW edge node from the reference edge defined
        by ref_node->this_node.

        Args:
            ref_node: The edge node reference.
            skip_spikes: Skip over edges that connect to nodes of order one.

        Returns:
            The counter-clockwise edge node closest to the reference node
            by angular distance. If all edges nodes are dead ends the
            reference node will be returned.
        """
        # Assume the edges have been already sorted in CCW order.
        node_index = self.index(ref_node) - 1
        node = self[node_index]
        while skip_spikes and node.degree() == 1 and node != ref_node:
            node_index -= 1
            node = self[node_index]
        return node

    def __eq__(self, other):
        """Compare for equality.
        GraphNodes are considered equal if their vertices are equal.
        This doesn't check if the outgoing edges are the same...
        """
        return other is not None and other.vertex == self.vertex

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.vertex)

    def __str__(self):
        """for debug output..."""
        return '%s [%d]' % (str(self.vertex), len(self))

class Graph(object):
    """Simple connected undirected 2D planar graph.
    """
    def __init__(self, edges=None):
        """
        Args:
            edges: An iterable collection of line segments that
                define the graph edges. Each edge connects two nodes.
                An edge being a 2-tuple of endpoints of the form:
                ((x1, y1), (x2, y2)).
        """
        #: Set of graph edges
        self.edges = set()
        #: Map of vertex points to graph nodes.
        self.nodemap = {}
        # Node at the lowest Y axis value.
        self._bottom_node = GraphNode(P.max_point())
        # Graph has been modified - i.e. nodes added or removed.
        self._modified = False

        if edges is not None:
            for edge in edges:
                self.add_edge(edge)

    def add_edge(self, edge):
        """
        Args:
            edge: A line segment that defines a graph edge.
                An edge being a 2-tuple of endpoints of the form:
                ((x1, y1), (x2, y2)).
        """
        edge_p1 = P(edge[0])
        edge_p2 = P(edge[1])
        # Check for degenerate edge...
        if edge_p1 == edge_p2:
            return
        edge = Line(edge_p1, edge_p2)
        if edge not in self.edges:
            self._check_modified(modify=True)
            self.edges.add(edge)
            # Build the node graph
            node1 = self.nodemap.get(edge_p1)
            if node1 is None:
                node1 = self._create_node(edge_p1)
            node2 = self.nodemap.get(edge_p2)
            if node2 is None:
                node2 = self._create_node(edge_p2)
            node1.add_edge_node(node2)
            node2.add_edge_node(node1)
            # Update bottom node
            if edge_p1.y < self._bottom_node.vertex.y:
                self._bottom_node = node1
            if edge_p2.y < self._bottom_node.vertex.y:
                self._bottom_node = node2

    def remove_edge(self, edge):
        """Remove and unlink the specified edge from the graph.

        Args:
            edge: A line segment that defines a graph edge
                connecting two nodes.
                An edge being a 2-tuple of endpoints of the form:
                ((x1, y1), (x2, y2)).
        """
        self._check_modified(modify=True)
        node1 = self.nodemap[edge.p1]
        node2 = self.nodemap[edge.p2]
        node1.remove(node2)
        node2.remove(node1)
        if node1.degree() == 0:
            del self.nodemap[edge.p1]
        if node2.degree() == 0:
            del self.nodemap[edge.p2]
        self.edges.remove(edge)

    def add_poly(self, vertices, close_poly=True):
        """Add edges from the line segments defined by
        the vertices of a polyline/polygon.

        Args:
            vertices: A list of polyline/polygon vertices as 2-tuples (x, y).
            close_poly: If True a closing segment will
                be automatically added if absent. Default is True.
        """
        p1 = vertices[0]
        for p2 in vertices[1:]:
            self.add_edge(Line(P(p1), P(p2)))
            p1 = p2
        if close_poly and vertices[0] != vertices[-1]:
            self.add_edge(Line(P(vertices[-1]),
                                       P(vertices[0])))

    def order(self):
        """Number of graph nodes (vertices.)"""
        return len(self.nodemap)

    def size(self):
        """Number of edges."""
        return len(self.edges)

    def vertices(self):
        """A collection view of node vertex points."""
        return self.nodemap.viewkeys()

    def boundary_polygon(self):
        """A polygon defining the outer edges of this segment graph.
        """
        self._check_modified(modify=False)
        return self._build_boundary_polygon(self._bottom_node, self.order())

    def peel_boundary_polygon(self, boundary_polygon):
        """Similar to convex hull peeling but with
        non-convex boundary polygons.

        Args:
            boundary_polygon: The initial graph polygon hull to peel.

        Returns:
            A list of peeled inner polygons. Possibly empty.
        """
        self._check_modified(modify=False)
        # Make a copy of the graph node map so that pruning won't
        # mutate this graph.
        nodemap = self._copy_nodemap()
        # Peel back the nodes outside and on the boundary
        self._prune_nodes(nodemap, boundary_polygon)
        poly_list = []
        while len(nodemap) > 3 and len(boundary_polygon) > 3:
            # Find the bottom-most node to start polygon march
            bottom_node = self._find_bottom_node(nodemap.viewvalues())
            # Get a new boundary polygon from peeled nodes
            boundary_polygon = self._build_boundary_polygon(bottom_node,
                                                           len(nodemap))
            if len(boundary_polygon) > 2:
                poly_list.append(boundary_polygon)
            # Peel the next layer
            self._prune_nodes(nodemap, boundary_polygon)
        return poly_list

    def cull_open_edges(self):
        """Remove edges that have one or two disconnected endpoints."""
        while True:
            open_edges = []
            for edge in self.edges:
                if (self.nodemap[edge.p1].degree() == 1
                        or self.nodemap[edge.p2].degree() == 1):
                    open_edges.append(edge)
            if not open_edges:
                break
            for edge in open_edges:
                self.remove_edge(edge)
        self._bottom_node = self._find_bottom_node(self.nodemap.viewvalues())

    def get_face_polygons(self):
        """Graph face polygons.

        Returns:
            A list of face polygons.
        """
        self._check_modified(modify=False)
        return make_face_polygons(self.edges, self.nodemap)

    def _remove_node(self, nodemap, node):
        """Remove and unlink a node from the node map."""
        if node.vertex in nodemap:
            # Remove edges connected to this node.
            for edge_node in node:
                if edge_node.vertex in nodemap:
                    edge_node.remove(node)
                    if edge_node.degree() == 0:
                        # The connected node is now orphaned so remove it also.
                        del nodemap[edge_node.vertex]
            del nodemap[node.vertex]

    def _create_node(self, vertex_point):
        """Create a graph node and insert it into the graph."""
        node = GraphNode(vertex_point)
        self.nodemap[vertex_point] = node
        return node

    def _check_modified(self, modify=False):
        """If the graph has been modified by adding or removing
        nodes then re-compute graph properties and sort the nodes.
        """
        if not modify and self._modified:
            for node in self.nodemap.values():
                node.sort_edges()
        self._modified = modify

    def _find_bottom_node(self, nodes):
        """Given a collection of graph nodes,
        return the node that has the minimum Y value.

        Args:
            nodes: An iterable collection or view of nodes.

        Returns:
            The bottom-most node.
        """
        if not nodes:
            return None
        iternodes = iter(nodes)
        bottom_node = iternodes.next()
        for node in iternodes:
            if node.vertex.y < bottom_node.vertex.y:
                bottom_node = node
        return bottom_node

    def _copy_nodemap(self):
        """Make a copy of the node map and edge connections of this graph.
        """
        nodemap_copy = {}
        # Copy the vertex->node mapping
        for vertex, node in self.nodemap.viewitems():
            nodemap_copy[vertex] = GraphNode(vertex)
        # Copy edge connections
        for node in nodemap_copy.viewvalues():
            srcnode = self.nodemap[node.vertex]
            for edge_node in srcnode:
                node.append(nodemap_copy[edge_node.vertex])
        return nodemap_copy

    def _prune_nodes(self, nodemap, boundary_polygon):
        """Prune the nodes corresponding to the list of points
        on or outside the specified polygon.
        """
        if boundary_polygon is not None and boundary_polygon:
            # Delete all the nodes outside the initial polygon.
            deleted_nodes = []
            for node in nodemap.viewvalues():
                if not polygon.point_inside(boundary_polygon, node.vertex):
                    deleted_nodes.append(node)
            for node in deleted_nodes:
                self._remove_node(nodemap, node)
            # Delete the nodes that correspond to the vertices of the polygon
            for vertex in boundary_polygon:
                node = nodemap.get(vertex)
                if node is not None:
                    self._remove_node(nodemap, node)
        # Remove any dead-end spike nodes
        while True:
            # List of vertices that will be deleted from the node map.
            deleted_nodes = []
            for node in nodemap.viewvalues():
                if node.degree() < 2:
                    deleted_nodes.append(node)
            if not deleted_nodes:
                break
            for node in deleted_nodes:
                self._remove_node(nodemap, node)

    def _build_boundary_polygon(self, start_node, num_nodes, prune_spikes=True):
        """Return a polygon defining the outer edges of a graph.

        Args:
            start_node: Should be the bottom-most node in the graph.
            num_nodes: The number of nodes in the graph.
            prune_spikes: Prune dangling edges from the boundary
                polygon. These would be edges that are connected to
                one node. Default is True.
        """
#         debug.draw_point(start_node.vertex, color='#ff0000')
        # If the start node only has one outgoing edge then
        # traverse it until a node with at least two edges is found.
        if prune_spikes and start_node.degree() == 1:
            start_node = start_node[0]
            num_nodes -= 1
            while start_node.degree() == 2:
                start_node = start_node.ccw_edge_node()
            if start_node.degree() == 1:
                # The graph is just a polyline...
                return []
#         debug.draw_point(start_node.vertex, color='#ff0000')
        # Perform a counter-clockwise walk around the outer edges
        # of the graph.
        boundary_polygon = [start_node.vertex,]
        curr_node = start_node
        prev_node = start_node[0]
        while num_nodes > 0:
            next_node = curr_node.ccw_edge_node(prev_node)
#             debug.draw_point(next_node.vertex, color='#00ff00')
            if not prune_spikes or next_node.degree() > 1:
                boundary_polygon.append(next_node.vertex)
            prev_node = curr_node
            curr_node = next_node
            num_nodes -= 1
            if curr_node == start_node:
                break
        return boundary_polygon


class GraphPathBuilder(object):
    """Given a Graph, build a set of paths
    made of connected graph edges.
    """
    PATH_STRAIGHTEST, PATH_SQUIGGLY, PATH_RANDOM, PATH_RANDOM2 = range(4)

    def __init__(self, graph):
        self.graph = graph
        self._random = random.Random()
        self._random.seed()

    def build_paths(self, start_edge=None, path_strategy=PATH_STRAIGHTEST):
        """Given the starting edge, find the set of edge paths that
        completely fill the graph...

        Args:
            start_edge: The graph edge that starts the path.
            path_strategy: How paths will be constructed. Possible
                pat strategies are:
                    PATH_STRAIGHTEST, PATH_SQUIGGLY,
                    PATH_RANDOM, and PATH_RANDOM2

        Returns:
            A list of paths sorted by descending order of path length.
        """
        if start_edge is None:
            start_edge = self._random.choice(list(self.graph.edges))
        paths = []
        free_edges = set(self.graph.edges)
        visited_edges = set()
        while free_edges:
            path = self._build_path(start_edge, visited_edges, path_strategy)
            paths.append(path)
            free_edges -= visited_edges
            if free_edges:
                start_edge = self._random.choice(list(free_edges))
        paths.sort(key=len, reverse=True)
        return paths

    def build_longest_paths(self, path_strategy=PATH_STRAIGHTEST):
        """Find the longest paths in this graph."""
        path_list = []
        for start_edge in self.graph.edges:
            visited_edges = set()
            path = self._build_path(start_edge, visited_edges, path_strategy)
            path_list.append(path)
        path_list.sort(key=len, reverse=True)
        return self._dedupe_paths(path_list)

    def _build_path(self, start_edge, visited_edges, path_strategy):
        """Build a path from the starting edge.
        Try both directions and glue the paths together."""
        node_a = self.graph.nodemap[start_edge[0]]
        node_b = self.graph.nodemap[start_edge[1]]
        path = self._build_path_forward(node_a, node_b, visited_edges,
                                        path_strategy)
        path_rev = self._build_path_forward(node_b, node_a, visited_edges,
                                            path_strategy)
        if len(path_rev) > 2:
            path.reverse()
            path.extend(path_rev[2:])
        return path

    def _build_path_forward(self, prev_node, curr_node,
                            visited_edges, path_strategy):
        """Starting at the specified node, follow outgoing edges until
        its no longer possible. Sort of a half-assed Euler tour...
        """
        path = [prev_node.vertex,]
        next_node = curr_node
        while next_node is not None:
            path.append(next_node.vertex)
            curr_node = next_node
            next_node = self._get_exit_edge_node(prev_node, curr_node,
                                                 visited_edges, path_strategy)
            edge = Line(prev_node.vertex, curr_node.vertex)
            visited_edges.add(edge)
            prev_node = curr_node
        return path

    def _get_exit_edge_node(self, prev_node, curr_node,
                            visited_edges, path_strategy):
        """Find an exit node that satisfies the path strategy.
        If all exit nodes define edges that have been already visited
        then return None."""
        if curr_node.degree() == 1:
            # End of the line...
            return None
        # List of potential exit nodes from the current node.
        exit_node_list = []
        for exit_node in curr_node:
            if exit_node != prev_node:
                edge = Line(curr_node.vertex, exit_node.vertex)
                if edge not in visited_edges:
                    exit_node_list.append(exit_node)
        exit_node = None
        if exit_node_list:
            # Sort the exit nodes in order of angular distance
            # from incoming edge.
            sortkey = lambda node: abs(curr_node.vertex.angle2(prev_node.vertex,
                                                               node.vertex))
            exit_node_list.sort(key=sortkey, reverse=True)
            if path_strategy == GraphPathBuilder.PATH_SQUIGGLY:
                exit_node = exit_node_list[-1]
            elif path_strategy == GraphPathBuilder.PATH_RANDOM:
                exit_node = self._random.choice(exit_node_list)
            elif path_strategy == GraphPathBuilder.PATH_RANDOM2:
                # A random choice weighted towards straighter paths
                exit_node_list.insert(0, exit_node_list[0])
                exit_node = self._random.choice(exit_node_list[0:3])
            else:
                exit_node = exit_node_list[0]
        return exit_node

    def _dedupe_paths(self, path_list, min_difference=2):
        """Remove similar paths from a list of paths.
        """
        deduped_path_list = [path_list[0],]
        prev_path = path_list[0]
        for path in path_list[1:]:
            pathset = frozenset(prev_path)
            if len(pathset.difference(path)) > min_difference:
                deduped_path_list.append(path)
            prev_path = path
        return deduped_path_list


class MarkedEdge(object):
    """A graph edge that is used to keep track of graph traversal direction.
    """
    def __init__(self, edge):
        """
        Args:
            edge: A graph edge (a Line segment).
        """
        self.edge = edge
        #: True if traversed in direction p2->p1, CCW winding
        self.visited_p1 = False
        #: True if traversed in direction p1->p2, CCW winding
        self.visited_p2 = False

    def visited_left(self, dest_vertex):
        """True if this edge has been visited with a CCW winding.
        The edge will be marked as visited.

        Args:
            dest_vertex: The destination vertex.
                Determines which side of the edge has been visited
                (i.e. direction).

        Returns:
            True if this edge has been visited during a counter-clockwise
            traversal. I.e. the left side given the direction.
            Otherwise False.
        """
        if dest_vertex == self.edge.p1:
            is_visited = self.visited_p1
            self.visited_p1 = True
        elif dest_vertex == self.edge.p2:
            is_visited = self.visited_p2
            self.visited_p2 = True
        else:
            assert(False)
        return is_visited


class MarkedEdgeMap(object):
    def __init__(self, edges):
        self._edgemap = dict()
        for edge in edges:
            self._edgemap[edge] = MarkedEdge(edge)

    def lookup(self, p1, p2):
        return self._edgemap[Line(p1, p2)]

    def mark_edge(self, p1, p2):
        marked_edge = self.lookup(p1, p2)
        marked_edge.visited_left(p2)


def make_face_polygons(edges, nodemap):
    """Given a graph, make polygons from graph faces delineated by edges.

    Args:
        nodemap: A mapping of edges to nodes.
    """
    # First mark the outside edges
    edgemap = MarkedEdgeMap(edges)
    faces = []
    for start_node in nodemap.viewvalues():
        # Find a free outgoing edge to start the walk
        next_node = find_free_edge_node(edgemap, start_node)
        while next_node is not None:
            face = make_face(edgemap, start_node, next_node)
            if face is not None and len(face) > 2:
                faces.append(face)
            # Keep going while there are free outgoing edges....
            next_node = find_free_edge_node(edgemap, start_node)
    return faces


def make_face(edgemap, start_node, next_node):
    # Start the counterclockwise walk
    face = [start_node.vertex, next_node.vertex,]
    prev_node = start_node
    curr_node = next_node
    while next_node != start_node and next_node.degree() > 1:
        next_node = curr_node.ccw_edge_node(prev_node, skip_spikes=False)
        if next_node.degree() == 1:
            edgemap.mark_edge(curr_node.vertex, next_node.vertex)
        else:
            face.append(next_node.vertex)
        edgemap.mark_edge(curr_node.vertex, next_node.vertex)
        prev_node = curr_node
        curr_node = next_node
    # Discard open, inside-out (clockwise wound), or unbounded faces.
    if next_node != start_node or polygon.area(face) > 0:
        return None
    return face

def find_free_edge_node(edgemap, start_node):
    # Find a free outgoing edge that is unmarked for CCW edge traversal
    next_node = None
    for edge_node in start_node:
        edge = edgemap.lookup(start_node.vertex, edge_node.vertex)
        if not edge.visited_left(edge_node.vertex) and edge_node.degree() > 1:
            next_node = edge_node
            break
    return next_node

