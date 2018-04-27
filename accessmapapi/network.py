'''Routing network initialization and definitions.'''
import numpy as np
import networkx as nx
import rtree
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
            attrs = ['geometry', 'incline', 'layer', 'length', 'side',
                     'street_name']
        elif path_type == 'crossing':
            attrs = ['geometry', 'curbramps', 'incline', 'layer', 'length',
                     'marked', 'street_name']
        elif path_type == 'elevator_path':
            attrs = ['geometry', 'indoor', 'layer', 'length', 'opening_hours',
                     'via']
        else:
            raise ValueError('Only the `sidewalk` and `crossing` path ' +
                             'types are allowed')

        gdf = gdf[gdf.columns & attrs]
        G = nx.Graph()

        def process_row(row):
            geometry = row['geometry']

            coords = list(geometry.coords)
            start = list(np.round(coords[0], PRECISION))
            end = list(np.round(coords[-1], PRECISION))

            start_node = str(start)
            end_node = str(end)

            # Add start node
            G.add_node(start_node, x=start[0], y=start[1])

            # Add end node
            G.add_node(end_node, x=end[0], y=end[1])

            # Add edge
            # retain original order in which geometry was added - necessary to
            # do costing based on directional attributes.
            row_attrs = row.to_dict()
            row_attrs['from'] = start_node
            row_attrs['to'] = end_node
            row_attrs['path_type'] = path_type
            row_attrs['length'] = round(row_attrs['length'], 1)

            G.add_edge(start_node, end_node, **row_attrs)

        gdf.apply(process_row, axis=1)

        return G

    G_sw = graph_from_gdf(sidewalks, 'sidewalk')
    G_cr = graph_from_gdf(crossings, 'crossing')
    G_el = graph_from_gdf(elevator_paths, 'elevator_path')

    G = nx.compose_all([G_sw, G_cr, G_el])

    return G


def make_sindex(G):
    sindex_list = []

    for node, d in G.nodes(data=True):
        # TODO: potential point for speedup - create bounds directly from x, y
        bounds = [d['x'], d['y'], d['x'], d['y']]
        # bounds = Point(d['x'], d['y']).bounds
        sindex_list.append([0, bounds, {'type': 'node', 'lookup': node}])

    for u, v, d in G.edges(data=True):
        bounds = d['geometry'].bounds
        sindex_list.append([0, bounds, {'type': 'edge', 'lookup': [u, v]}])

    sindex = rtree.index.Index(sindex_list)

    return sindex, sindex_list
