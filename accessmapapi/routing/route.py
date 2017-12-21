import geojson
import networkx as nx
from shapely.geometry import mapping
from accessmapapi import network_handlers
from . import costs


def dijkstra(origin, destination, cost_fun_gen=costs.cost_fun_generator,
             cost_kwargs=None):
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

    G, sindex = network_handlers.get_G()
    if G is None:
        raise ValueError('Routing network could not be initialized')

    cost_fun = costs.cost_fun_generator(**cost_kwargs)

    # The graph is a MultiDiGraph, so there may be multiple pieces of data
    # sent to the cost function. We're ignoring this for now, and just
    # choosing the first edge data.
    # def wrapped_cost_fun(u, v, d):
    #     return cost_fun(u, v, d)

    # Find closest edge or node to points
    def initialization_points(point):
        query = sindex.nearest(point.bounds, 1, objects=True)
        closest = [q.object for q in query][0]
        if closest['type'] == 'node':
            nodes = [closest['lookup']]
            node_costs = [0]
        else:
            # It's an edge! TODO: do things (for now just grab first point)
            nodes = [closest['lookup'][0]]
            node_costs = [0]

        return nodes, node_costs

    origins, origin_costs = initialization_points(origin)
    destinations, destination_costs = initialization_points(destination)

    paths_data = []
    for o, cost_o in zip(origins, origin_costs):
        for d, cost_d in zip(destinations, destination_costs):
            if o == d:
                # Start and end points are the same - no route!
                continue

            path_data = geojson.FeatureCollection([])

            try:
                # TODO: Use single_source_dijkstra so the graph doesn't have
                # to be traversed again to find the total cost
                # TODO: consider just reimplementing custom dijkstra so that
                # temporary edges/costing can be used and more custom behavior
                # can be encoded (such as infinite costs). NetworkX
                # implementation is under networkx>algorithms>shortest_paths>
                # weighted: _dijkstra_multisource
                # TODO: reimplementing dijkstra is probably a good idea
                # anyways, to make following the 'reverse' path possible
                # without doubling + complicating the graph.
                total_cost, path = nx.bidirectional_dijkstra(G, o, d,
                                                             weight=cost_fun)
            except nx.NetworkXNoPath:
                continue

            # total_cost = 0
            for node_id1, node_id2 in zip(path[:-1], path[1:]):
                node1 = G.nodes[node_id1]
                node2 = G.nodes[node_id2]
                edge = G[node_id1][node_id2]

                cost = cost_fun(node1, node2, edge)

                feature = geojson.Feature()
                feature['geometry'] = mapping(edge['geometry'])
                if edge['path_type'] == 'sidewalk':
                    feature['properties'] = {
                        'path_type': edge['path_type'],
                        'cost': cost,
                        'length': edge['length'],
                        'incline': edge['incline']
                    }
                elif edge['path_type'] == 'crossing':
                    feature['properties'] = {
                        'path_type': edge['path_type'],
                        'cost': cost,
                        'length': edge['length'],
                        'curbramps': edge['curbramps']
                    }

                if edge['from'] != node_id1:
                    # Traversed edge in opposite direction as geometry

                    # Reverse coordinates
                    new_coords = list(reversed(edge['geometry'].coords))
                    feature['geometry']['coordinates'] = new_coords

                    # Reverse incline, if applicable
                    if 'incline' in feature['properties']:
                        new_incline = -1.0 * feature['properties']['incline']
                        feature['properties']['incline'] = new_incline

                path_data['features'].append(feature)

            total_cost += cost_o
            total_cost += cost_d

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

    coords = []
    segments = geojson.FeatureCollection([])
    for feature in best_path['features']:
        segments['features'].append(feature)
        coords += feature['geometry']['coordinates']

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
    origin_feature = {'type': 'Feature',
                      'geometry': {
                        'type': 'Point',
                        'coordinates': list(origin.coords)
                      },
                      'properties': {}}

    dest_feature = {'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': list(destination.coords)
                    },
                    'properties': {}}
    waypoints_feature_list = []
    for waypoint in [origin, destination]:
        waypoint_feature = {
            'type': 'Feature',
            'geometry': {
              'type': 'Point',
              'coordinates': list(waypoint.coords)
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

    routes.append(route)

    route_response = {}
    route_response['origin'] = origin_feature
    route_response['destination'] = dest_feature
    route_response['waypoints'] = waypoints_feature_list
    route_response['routes'] = routes
    route_response['code'] = 'Ok'

    return route_response
