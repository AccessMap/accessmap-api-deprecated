'''Routing network initialization and definitions.'''
import math
import numpy as np
import networkx as nx
import rtree
from shapely.geometry import Point


def make_network(sidewalks, crossings, sindex_path):
    '''Create a network given sidewalk and crossing data. Expectation is that
    the data is already 'noded', i.e. that all lines that should be connected
    roughly end-to-end.

    :param sidewalks: Sidewalks dataset
    :type sidewalks: geopandas.GeoDataFrame
    :param crossings: Crossings dataset
    :type crossings: geopandas.GeoDataFrame

    '''
    # Precision for rounding, in latlon degrees.
    PRECISION = 7

    # We'll also create a spatial index so we can look up nodes/edges quickly!
    sindex = rtree.index.Index(sindex_path)

    def graph_from_gdf(gdf, path_type):
        gdf['length'] = gdf.geometry.apply(lambda x: haversine(x.coords))
        sidewalk_attrs = ['geometry', 'layer', 'length', 'incline']
        crossing_attrs = ['geometry', 'layer', 'length', 'incline',
                          'curbramps', 'marked']
        if path_type == 'sidewalk':
            attrs = sidewalk_attrs
        elif path_type == 'crossing':
            attrs = crossing_attrs
        else:
            raise ValueError('Only the `sidewalk` and `crossing` path ' +
                             'types are allowed')
        G = nx.MultiDiGraph()
        for idx, row in gdf.iterrows():
            geometry = row['geometry']
            row_attrs = dict(row[row.index & attrs])

            start = list(np.round(geometry.coords[0], PRECISION))
            end = list(np.round(geometry.coords[-1], PRECISION))

            start_node = str(start)
            end_node = str(end)

            # Add start node
            G.add_node(start_node, x=start[0], y=start[1])
            obj_s = {
                'type': 'node',
                'lookup': start_node
            }
            sindex.insert(0, Point(start).bounds, obj_s)

            # Add end node
            G.add_node(end_node, x=end[0], y=end[1])
            obj_e = {
                'type': 'node',
                'lookup': end_node
            }
            sindex.insert(0, Point(end).bounds, obj_e)

            # Add edge
            G.add_edge(start_node, end_node, path_type=path_type,
                       **row_attrs)
            obj_v = {
                'type': 'edge',
                'lookup': [start_node, end_node]
            }
            sindex.insert(0, geometry.bounds, obj_v)

        return G

    G_sw = graph_from_gdf(sidewalks, 'sidewalk')
    G_cr = graph_from_gdf(crossings, 'crossing')

    G = nx.compose(G_sw, G_cr)
    G

    return G, sindex


def haversine(coords):
    # Given a list of coordinates (e.g. linestring.coords), calculate the
    # great circle length of the line, in meters
    d = 0
    for i, coord in enumerate(coords):
        if i == 0:
            pass
        last_coord = coords[i - 1]

        x1, y1 = last_coord
        x2, y2 = coord

        radius = 6371  # km
        dx = math.radians(x2 - x1)
        dy = math.radians(y2 - y1)

        a = math.sin(dy / 2) * math.sin(dy / 2) + \
            math.cos(math.radians(y1)) * math.cos(math.radians(y2)) * \
            math.sin(dx / 2) * math.sin(dx / 2)

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        d_km = radius * c
        d += d_km * 1000.

    return d
