import copy
from shapely.geometry import mapping, LineString
from shapely import wkt
from accessmapapi.constants import DEFAULT_COLS
from accessmapapi.graph import query
from accessmapapi.utils import strip_null_fields, fields_with_geom
from accessmapapi import exceptions
from accessmapapi.models import edge_factory, GeometryField
from . import costs
from .dijkstra import dijkstra_multi

# TODO: what to do with partial paths? e.g. a path might take 20 mins to walk by itself
# and would not show up on the walkshed - how to best implement the notion of a
# 'partial' walkshed that is time + cost-function based? (probably just binary search
# with the cost function).


def walkshed(lon, lat, cost_fun_gen=costs.cost_fun_generator,
             cost_kwargs=None, max_cost=None, only_valid=True, layers=None):
    '''Produce a limited-time walkshed given a user-customizable cost function.

    :param lon: longitude of the starting location.
    :type lon: length 2 iterable of numbers.
    :param lat: longitude of the starting location.
    :type lat: length 2 iterable of numbers.
    :param cost_fun_gen: Function that generates a cost function given the
           info from `cost_kwargs`.
    :type cost_fun_gen: callable
    :param cost_kwargs: keyword arguments to pass to the cost function.
    :type cost_kwargs: dict
    :param max_cost: Maximum cost of traversal - search will go no farther.
    :type max_cost: float

    '''
    if max_cost is None:
        max_cost = 10
    if layers is None:
        columns = DEFAULT_COLS
    else:
        columns = {}
        sources = []
        for name, layer in layers.items():
            for propname, value in layer['properties'].items():
                columns[propname] = value['type']
        columns['way'] = 'varchar'
        columns['u'] = 'integer'
        columns['v'] = 'integer'
        columns['forward'] = 'integer'

    Edge = edge_factory(columns)
    Edge._meta.add_field('geometry', GeometryField())

    # Query the start and end points for viable features
    if cost_kwargs is None:
        cost_fun = cost_fun_gen()
    else:
        cost_fun = cost_fun_gen(**cost_kwargs)

    origin = query.closest_valid_startpoints(Edge, lon, lat, 100, cost_fun)[0]
    sources = [origin['node']]
    if origin is None:
        return {
            'code': 'NoValidNearby',
            'waypoints': [],
            'routes': []
        }

    try:
        # If starting point is along edge, we'll be creating an out-of-database
        # node and two edges.
        # We can speed up the shortest path calculation by giving
        # dijkstra_multi *both* in-graph starting points
        total_cost, paths = dijkstra_multi(Edge, sources, cost_fun, cutoff=max_cost)
    except exceptions.NoPath:
        return {
            'code': 'NoPath',
            'geometry': {},
        }

    # We got an in-database path! Now we need to add back the non-database parts
    # like temporary split edges
    # Extract all unique edges
    unique_edges = set([])
    for destination, path in paths.items():
        for u, v in zip(path[:-1], path[1:]):
            unique_edges.add((u, v))

    fields = fields_with_geom(Edge)
    path_data = {'type': 'FeatureCollection', 'features': []}
    if 'initial_edge' in origin:
        strip_null_fields(origin['initial_edge'])
        feature1 = edge_to_feature(origin['initial_edge'],
                                   origin['initial_cost'])
        path_data['features'].append(feature1)
    for u, v in unique_edges:
        # TODO: potential point for optimization
        q = Edge.select(*fields).where((Edge.u == u) & (Edge.v == v))
        edge = list(q.dicts())[0]
        # Remove null / none-ish values. TODO: extract into function
        strip_null_fields(edge)
        cost = cost_fun(u, v, edge)
        # TODO: figure out why the column name for geoms have trailing quotes.
        edge['geometry'] = wkt.loads(edge['geometry")'])
        edge.pop('geometry")')
        feature = edge_to_feature(edge, cost)
        path_data['features'].append(feature)

    return path_data

def edge_to_feature(edge, cost):
    feature = {'type': 'Feature', 'properties': {}}

    # Prevent editing of original edge
    edge = copy.deepcopy(edge)

    feature['geometry'] = mapping(edge['geometry'])

    edge['cost'] = cost

    edge.pop('u')
    edge.pop('v')
    edge.pop('geometry')

    feature['properties'] = edge

    return feature
