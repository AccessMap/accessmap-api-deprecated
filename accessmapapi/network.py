'''Routing network initialization and definitions.'''
import numpy as np
import networkx as nx
import rtree
from shapely.geometry import Point
from accessmapapi.utils import haversine


def make_network(sidewalks, crossings, elevator_paths):
    '''Create a network given sidewalk and crossing data. Expectation is that
    the data is already 'noded', i.e. that all lines that should be connected
    roughly end-to-end.

    :param sidewalks: Sidewalks dataset
    :type sidewalks: geopandas.GeoDataFrame
    :param crossings: Crossings dataset
    :type crossings: geopandas.GeoDataFrame
    :param elevator_paths: Elevator paths dataset
    :type elevator_paths: geopandas.GeoDataFrame

    '''
    # Precision for rounding, in latlon degrees.
    PRECISION = 7

    # We'll also create a spatial index so we can look up nodes/edges quickly!
    def graph_from_gdf(gdf, path_type):
        gdf['length'] = gdf.geometry.apply(lambda x: haversine(x.coords))

        if path_type == 'sidewalk':
            attrs = ['geometry', 'layer', 'length', 'incline']
        elif path_type == 'crossing':
            attrs = ['geometry', 'layer', 'length', 'incline', 'curbramps',
                     'marked']
        elif path_type == 'elevator_path':
            attrs = ['geometry', 'indoor', 'layer', 'opening_hours', 'via']
        else:
            raise ValueError('Only the `sidewalk` and `crossing` path ' +
                             'types are allowed')

        G = nx.Graph()
        for idx, row in gdf.iterrows():
            geometry = row['geometry']
            row_attrs = dict(row[row.index & attrs])

            start = list(np.round(geometry.coords[0], PRECISION))
            end = list(np.round(geometry.coords[-1], PRECISION))

            start_node = str(start)
            end_node = str(end)

            # Add start node
            G.add_node(start_node, x=start[0], y=start[1])

            # Add end node
            G.add_node(end_node, x=end[0], y=end[1])

            # Add edge
            # retain original order in which geometry was added - necessary to
            # do costing based on directional attributes.
            row_attrs['from'] = start_node
            row_attrs['to'] = end_node

            G.add_edge(start_node, end_node, path_type=path_type,
                       **row_attrs)

        return G

    G_sw = graph_from_gdf(sidewalks, 'sidewalk')
    G_cr = graph_from_gdf(crossings, 'crossing')
    G_el = graph_from_gdf(elevator_paths, 'elevator_path')

    G = nx.compose(G_sw, G_cr, G_el)
    G

    return G


def make_sindex(G):
    sindex = rtree.index.Index()

    for node, d in G.nodes(data=True):
        # TODO: potential point for speedup - create bounds directly from x, y
        sindex.insert(0, Point(d['x'], d['y']).bounds, {
            'type': 'node',
            'lookup': node
        })

    for u, v, d in G.edges(data=True):
        sindex.insert(0, d['geometry'].bounds, {
            'type': 'edge',
            'lookup': [u, v]
        })

    return sindex
