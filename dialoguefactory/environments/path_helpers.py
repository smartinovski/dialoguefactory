#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module lists all the functions needed for finding the shortest path between two entities in the world.
"""
import dijkstar


def cost_function(ent1, ent2, edge, prev_edge):
    """ Returns the edge cost.
        When finding the path between two locations,
        the edge is a tuple of two values. The first value is the cost of movement, and
        the second value is the direction that leads from the source location to the target location.
    """
    return edge[0]


def find_shortest_path(source, target, graph):
    """
        Finds the shortest path between the source and the target using the graph.

        Parameters
        ----------
        source : Entity
            The starting location.
        target : Entity
            The end location.
        graph : dijkstar.Graph
            The edges of the graph connect two vertices (the source and target location)

        Returns
        -------
        path : list
            Returns the path, which is a list of directions.
    """
    try:
        path_info = dijkstar.find_path(graph, source, target, cost_func=cost_function)
    except Exception:
        path_info = None

    if path_info is None:
        return None

    edges = path_info.edges

    path = []
    for edge in edges:
        path.append(edge[1])

    return path
