import copy
import geojson
import math
import networkx as nx
import pyproj
from shapely import ops
from shapely.geometry import mapping
from accessmapapi import app, graph, utils
from . import costs


def dijkstra(origin, destination, cost_fun_gen=costs.cost_fun_generator,
             cost_kwargs=None, only_valid=True):
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
    #
    # Strategy:
    #
    # 1. Find the closest point in the network for origin and destination.
    # 2. If the closest point is on an edge (as opposed to endpoint/node), will
    #    actually find two routes, starting on the edge, and append the cost
    #    of that partial traversal to the total + create extra geometries. This
    #    means that way may find 4 routes. Wasteful, but without a way to add
    #    temporary edges / implement dijkstra ourselves, it's the only option.
    # 3. Route from every start to every end.
    # 4. Pick the lowest-cost route, return its data according to the spec
    #    used by Mapbox.
    '''
    NOTE: Picking the 'closest' edge or node is not enough: we should make
    some kind of educated guess based on the environment they'd have to
    traverse. Eventually, this would mean finding a building exit (or several),
    but for now, we can do things like avoid crossing any footpaths.

    So, new strategy: iterate over 'nearest' paths/nodes until one of the
    following conditions is met:

    1. We've reached a maximum distance metric (e.g all within 100 meters)
    2. We've found a path we can reach without intersection any other paths.

    '''
    G = app.config.get('G', None)
    sindex = app.config.get('sindex', None)
    if (G is None) or (sindex is None):
        if G is None:
            app.logger.warn('Got request for routing, but the graph does ' +
                            'not exist yet.')
            code = 'GraphNotReady'
        elif sindex is None:
            app.logger.warn('Got request for routing, but the spatial index ' +
                            'does not exist yet.')
            code = 'SpatialIndexNotReady'

        return {
            'code': code,
            'waypoints': [],
            'routes': []
        }

    cost_fun = costs.cost_fun_generator(**cost_kwargs)

    # The graph is a MultiDiGraph, so there may be multiple pieces of data
    # sent to the cost function. We're ignoring this for now, and just
    # choosing the first edge data.
    # def wrapped_cost_fun(u, v, d):
    #     return cost_fun(u, v, d)

    # Find closest edge or node to points
    def initialization_points(point):
        '''Find these data, given a query point starting anywhere in the world:
            1. The closest point in the dataset to the query.
            2. The initial cost(s) to travel from that point to the nearest
            node(s) in the graph (0 if the closest point was already a node)
            3. The nodes to start dijkstra at - e.g. if an edge was found,
            it's the start and end nodes.

            Returned as a list of dicts of this format:
            [{
                'initial_edge': 'fake' graph edge if starting mid-way on an
                                edge,
                'initial_cost': float,
                'node': node ID in networkx graph
            }]

        '''

        def is_valid(edge):
            return cost_fun(1, 2, edge) != math.inf

        if only_valid:
            valid_filter = is_valid
        else:
            valid_filter = None

        closest = graph.query.closest_nonintersecting_edge(G, sindex, point.x,
                                                           point.y, 100,
                                                           filter=valid_filter)

        if closest is None:
            return None

        # Closest point on that feature
        utm_zone_epsg = utils.lonlat_to_utm_epsg(point.x, point.y)
        wgs84 = pyproj.Proj(init='epsg:4326')
        utm = pyproj.Proj(init='epsg:{}'.format(utm_zone_epsg))

        def proj_wgs84(x, y):
            return pyproj.transform(utm, wgs84, x, y)

        def proj_utm(x, y):
            return pyproj.transform(wgs84, utm, x, y)

        center_utm = ops.transform(proj_utm, point)
        geom_utm = ops.transform(proj_utm, closest['geometry'])
        distance_along = geom_utm.project(center_utm)

        # Decide whether to return the edge of point
        if distance_along < 0.1:
            # We should use the 'start' node
            closest = {
                'type': 'node',
                'lookup': closest['from']
            }
        elif (geom_utm.length - distance_along) < 0.1:
            # We should use the 'end' node
            closest = {
                'type': 'node',
                'lookup': closest['to']
            }
        else:
            # We should use the edge.
            fraction_along = geom_utm.project(center_utm, normalized=True)
            distance = geom_utm.length * fraction_along
            geom_u, geom_v = utils.cut(geom_utm, distance)
            length_u = geom_u.length
            length_v = geom_v.length
            geom_u_wgs84 = ops.transform(proj_wgs84, geom_u)
            geom_v_wgs84 = ops.transform(proj_wgs84, geom_v)

            closest = {
                'type': 'edge',
                'lookup': [closest['from'], closest['to']],
                'geometry_u': geom_u_wgs84,
                'length_u': length_u,
                'geometry_v': geom_v_wgs84,
                'length_v': length_v,
            }

        # FIXME: this does not actually find the closest geometry, just the
        # closest sindex entry. We need a proper, in-meters, 'closest' function
        if closest['type'] == 'node':
            # It's a node! Easy-peasy
            results = [{
                'initial_cost': 0,
                'node': closest['lookup']
            }]
        else:
            # It's an edge! Need to split it and calculate initial trip costs
            u, v = closest['lookup']

            # 1. Set aside edge copies for modification
            edge = G[u][v]
            edge_u = copy.deepcopy(edge)
            edge_v = copy.deepcopy(edge)

            # the graph is undirected, so we need to re-extract u and v from
            # the edge to maintain their correspondence
            # TODO: Use a DiGraph? Doubles graph size...
            u = edge['from']
            v = edge['to']

            # 2. Save the new geometries and lengths
            edge_u['geometry'] = closest['geometry_u']
            edge_v['geometry'] = closest['geometry_v']

            edge_u['length'] = closest['length_u']
            edge_v['length'] = closest['length_v']

            edge_u['to'] = -1
            edge_v['from'] = -1

            # 4. Add initial costs
            # NOTE: u and v only communicate directionality right now - the
            # first argument to cost_fun doesn't have to be perfectly accurate.
            cost_u = cost_fun(u, -1, edge_u)
            cost_v = cost_fun(-1, v, edge_v)

            # 5. Save the edge
            result_u = {
                'node': u,
                'initial_cost': cost_u,
                'initial_edge': edge_u
            }

            result_v = {
                'node': v,
                'initial_cost': cost_v,
                'initial_edge': edge_v
            }

            results = [result_u, result_v]

        return results

    origins = initialization_points(origin)
    destinations = initialization_points(destination)

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

    paths_data = []
    for o in origins:
        for d in destinations:
            if o == d:
                # Start and end points are the same - no route!
                continue
            # FIXME: We also need to check starting on the same edge as a
            # special case - should evaluate cost of traversing partial
            # segment vs. going to endpoints.

            path_data = geojson.FeatureCollection([])

            try:
                # TODO: consider just reimplementing custom dijkstra so that
                # temporary edges/costing can be used and more custom behavior
                # can be encoded (such as infinite costs). NetworkX
                # implementation is under networkx>algorithms>shortest_paths>
                # weighted: _dijkstra_multisource
                total_cost, path = nx.single_source_dijkstra(G, o['node'],
                                                             d['node'],
                                                             weight=cost_fun)
            except nx.NetworkXNoPath:
                continue

            if 'initial_edge' in o:
                reverse = o['initial_edge']['to'] == -1
                feature1 = edge_to_feature(o['initial_edge'],
                                           o['initial_cost'],
                                           reverse)
                path_data['features'].append(feature1)

            for u, v in zip(path[:-1], path[1:]):
                edge = G[u][v]

                cost = cost_fun(u, v, edge)

                reverse = edge['from'] != u

                feature = edge_to_feature(edge, cost, reverse)

                path_data['features'].append(feature)

            if 'initial_edge' in d:
                reverse = d['initial_edge']['from'] == -1
                feature2 = edge_to_feature(d['initial_edge'],
                                           d['initial_cost'],
                                           reverse)
                path_data['features'].append(feature2)

            total_cost += o['initial_cost']
            total_cost += d['initial_cost']

            path_data['total_cost'] = total_cost
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

    # Start at first point
    segments = geojson.FeatureCollection([])
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
    origin_feature = geojson.Feature()
    origin_feature['geometry'] = mapping(origin)
    destination_feature = geojson.Feature()
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

    # TODO: Add steps!
    route['steps'] = []
    route['summary'] = ''
    route['total_cost'] = best_path['total_cost']

    routes.append(route)

    route_response = {}
    route_response['origin'] = origin_feature
    route_response['destination'] = destination_feature
    route_response['waypoints'] = waypoints_feature_list
    route_response['routes'] = routes
    route_response['code'] = 'Ok'

    return route_response


def edge_to_feature(edge, cost, reverse=False):
    feature = geojson.Feature()

    # Prevent editing of original edge
    edge = copy.deepcopy(edge)

    if reverse:
        coords = list(reversed(edge['geometry'].coords))
        edge['geometry'].coords = coords

        if 'incline' in edge:
            edge['incline'] = -1.0 * edge['incline']

    feature['geometry'] = mapping(edge['geometry'])

    edge['cost'] = cost

    edge.pop('from')
    edge.pop('to')
    edge.pop('geometry')

    feature['properties'] = edge

    return feature
