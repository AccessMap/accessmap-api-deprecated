import copy
import math
from shapely.geometry import mapping, LineString
from shapely import wkt
from accessmapapi.constants import DEFAULT_COLS
from accessmapapi.build.featuresource import FeatureSource
from accessmapapi.graph import query
from accessmapapi.utils import cut, haversine, strip_null_fields, fields_with_geom
from accessmapapi import exceptions
from accessmapapi.models import edge_factory, GeometryField
from . import costs
from . import directions
from .dijkstra import dijkstra_multi


def dijkstra(origin, destination,
             cost_fun_gen=costs.cost_fun_generator, cost_kwargs=None,
             only_valid=True, layers=None):
    '''Process a routing request, returning a Mapbox-compatible routing JSON
    object.

    :param origin: lat-lon of starting location.
    :type origin: list of coordinates
    :param destination: lat-lon of ending location.
    :type destination: list of coordinates
    :param cost_fun_gen: Function that generates a cost function given the
           info from `cost_kwargs`.
    :type cost_fun_gen: callable
    :param cost_kwargs: keyword arguments to pass to the cost function.
    :type cost_kwargs: dict

    '''
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
    origins = query.closest_valid_startpoints(Edge, origin.x, origin.y,
                                              100, cost_fun)
    destinations = query.closest_valid_startpoints(Edge, destination.x,
                                                   destination.y, 100,
                                                   cost_fun, dest=True)

    if origins is None:
        if destinations is None:
            return {
                'code': 'BothFarAway',
                'waypoints': [],
                'routes': []
            }
        else:
            return {
                'code': 'OriginFarAway',
                'waypoints': [],
                'routes': []
            }
    else:
        if destinations is None:
            return {
                'code': 'DestinationFarAway',
                'waypoints': [],
                'routes': []
            }

    # TODO: consider case where origin and destination nodes are identical. Should
    # essentially just ignore the route and/or get nothing from the path, but still
    # return lines to/from origin and destination to graph.
    paths_data = []
    for d in destinations:
        origin_nodes = [o['node'] for o in origins]
        path_data = {'type': 'FeatureCollection', 'features': []}
        try:
            # If starting point is along edge, we'll be creating an out-of-database
            # node and two edges.
            # We can speed up the shortest path calculation by giving
            # dijkstra_multi *both* in-graph starting points
            total_cost, path = dijkstra_multi(Edge, origin_nodes, cost_fun,
                                              target=d['node'])
        except exceptions.NoPath:
            continue

        # We got an in-database path! Now we need to add back the non-database parts
        # like temporary split edges
        # TODO: key origins by their node ID for faster lookup later + organization
        match = [o for o in origins if o['node'] == path[0]]
        if not match:
            return {
                'code': 'Internal Error',
                'waypoints': [],
                'routes': []
            }

        o = match[0]

        if 'initial_edge' in o:
            strip_null_fields(o['initial_edge'])
            feature1 = edge_to_feature(o['initial_edge'],
                                       o['initial_cost'])
            path_data['features'].append(feature1)

        fields = fields_with_geom(Edge)
        for u, v in zip(path[:-1], path[1:]):
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

        if 'initial_edge' in d:
            strip_null_fields(d['initial_edge'])
            feature2 = edge_to_feature(d['initial_edge'],
                                       d['initial_cost'])
            path_data['features'].append(feature2)

        total_cost += o['initial_cost']
        total_cost += d['initial_cost']

        path_data['total_cost'] = total_cost
        paths_data.append(path_data)

    # Special case: if it's on the same path, also consider the same-path route
    if 'original_edge' in origins[0] and 'original_edge' in destinations[0]:
        if origins[0]['original_edge'] == destinations[0]['original_edge']:
            o = origins[0]
            d = destinations[0]
            # The start and end are on the same path. Consider only the on-edge
            # path.
            between = copy.deepcopy(o['original_edge'])

            o_diff = o['initial_edge']['length'] - o['original_edge']['length']
            d_diff = d['initial_edge']['length'] - o['original_edge']['length']
            between['length'] = between['length'] - o_diff - d_diff

            o_along = between['geometry'].project(o['point'])
            d_along = between['geometry'].project(d['point'])
            first, second = reversed(sorted([o_along, d_along]))
            line = between['geometry']
            line, _ = cut(between['geometry'], first)
            _, line = cut(line, second)

            if o_along > d_along:
                # Going in the reverse direction
                coords = reversed(line.coords)
                line = LineString(coords)
                between['incline'] = -1.0 * between['incline']

            between['geometry'] = line
            between['length'] = haversine(line.coords)

            path_data = { 'type': 'FeatureCollection', 'features': []}
            cost = cost_fun(-1, -2, between)
            path_data['total_cost'] = cost
            feature = edge_to_feature(between, cost)
            path_data.features.append(feature)
            paths_data.append(path_data)

    if paths_data:
        best_path = sorted(paths_data, key=lambda x: x['total_cost'])[0]
    else:
        return {
            'code': 'NoRoute',
            'waypoints': [],
            'routes': []
        }

    if best_path['total_cost'] == math.inf:
        # Note valid paths were found.
        # TODO: extract something more informative so users know what params
        # to relax.
        return {
            'code': 'NoRoute',
            'waypoints': [],
            'routes': []
        }

    # TODO: normalize coordinate values (round to 7th decimal precision)

    # Start at first point
    segments = {'type': 'FeatureCollection', 'features': []}
    coords = [best_path['features'][0]['geometry']['coordinates'][0]]
    for feature in best_path['features']:
        segments['features'].append(feature)
        coords += feature['geometry']['coordinates'][1:]

    # Produce the response
    # TODO: return JSON directions similar to Mapbox or OSRM so e.g.
    # leaflet-routing-machine can be used
    '''
    Format:
    JSON hash with:
        origin: geoJSON Feature with Point geometry for start point of route
        destination: geoJSON Feature with Point geometry for end point of route
        waypoints: array of geoJSON Feature Points
        routes: array of routes in descending order (just 1 for now):
            summary: A short, human-readable summary of the route. DISABLED.
            geometry: geoJSON LineString of the route (OSRM/Mapbox use
                      polyline, often)
            steps: optional array of route steps (directions/maneuvers).
                   (NOT IMPLEMENTED YET)
                way_name: way along which travel proceeds
                direction: cardinal direction (e.g. N, SW, E, etc)
                maneuver: JSON object representing the maneuver
                    No spec yet, but will mirror driving directions:
                        type: string of type of maneuver (short) e.g. cross
                              left/right
                        location: geoJSON Point geometry of maneuver location
                        instruction: e.g.
                            turn left and cross <street> on near side


    TODO:
        Add these to routes:
            distance: distance of route in meters
        Add these to steps:
            distance: distance from step maneuver to next step
            heading: what is this for? Drawing an arrow maybe?
    '''
    origin_feature = {'type': 'Feature', 'properties': {}}
    origin_feature['geometry'] = mapping(origin)
    destination_feature = {'type': 'Feature', 'properties': {}}
    destination_feature['geometry'] = mapping(destination)

    waypoints_feature_list = []
    for waypoint in [origin, destination]:
        waypoint_feature = {
            'type': 'Feature',
            'geometry': {
              'type': 'Point',
              'coordinates': waypoint.coords[0]
            },
            'properties': {}
        }
        waypoints_feature_list.append(waypoint_feature)

    # TODO: here's where to add alternative routes once we have them
    routes = []
    route = {}
    route['geometry'] = {
        'type': 'LineString',
        'coordinates': coords
    }

    # Add annotated segment GeoJSON FeatureCollection
    route['segments'] = segments

    # Extract steps information
    track = [
        'curbramps',
        'incline',
        'indoor',
        'length',
        'marked',
        'side',
        'street_name',
        'surface',
        'via'
    ]
    steps_data = directions.path_to_directions(best_path, track)

    # TODO: Add steps!
    route['legs'] = []
    route['legs'].append(steps_data)
    route['summary'] = ''
    route['duration'] = int(best_path['total_cost'])
    total_distance = 0
    for feature in best_path['features']:
        total_distance += feature['properties']['length']
    route['distance'] = round(total_distance, 1)
    route['total_cost'] = round(best_path['total_cost'], 2)

    routes.append(route)

    route_response = {}
    route_response['origin'] = origin_feature
    route_response['destination'] = destination_feature
    route_response['waypoints'] = waypoints_feature_list
    route_response['routes'] = routes
    route_response['code'] = 'Ok'

    return route_response


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
