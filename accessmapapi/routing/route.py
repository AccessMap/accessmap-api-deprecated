import copy
import geojson
import networkx as nx
from shapely.geometry import mapping
from accessmapapi import app, utils
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
    G = app.config.get('G', None)
    sindex = app.config.get('sindex', None)
    if (G is None) or (sindex is None):
        app.logger.warn('Got request for graph, but it does not exist yet.')

        return {
            'code': 'GraphNotReady',
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
    def initialization_points(point, point_type):
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
        query = sindex.nearest(point.bounds, 1, objects=True)
        closest = [q.object for q in query][0]
        if closest['type'] == 'node':
            results = [{
                'initial_cost': 0,
                'node': closest['lookup']
            }]
        else:
            # It's an edge! Need to generate two nodes and two fake edges
            node1, node2 = closest['lookup']

            result1 = {
                'node': node1
            }

            result2 = {
                'node': node2
            }

            # Calculate partial costs. Note: the cost function is getting
            # inserted here - not generalizable!

            # 1. Set aside two copies of the edge
            edge1 = copy.deepcopy(G[node1][node2])
            edge2 = copy.deepcopy(G[node1][node2])

            # 2. Recalculate the length, cut the geometry
            fraction_along = edge1['geometry'].project(point, normalized=True)
            distance = edge1['geometry'].length * fraction_along
            geom1, geom2 = utils.cut(edge1['geometry'], distance)

            # 3. Save the new geometries and lengths
            edge1['length'] = fraction_along * edge1['length']
            edge2['length'] = (1.0 - fraction_along) * edge2['length']
            edge1['geometry'] = geom1
            edge2['geometry'] = geom2

            # 4. Reverse geometries depending on point type
            # If it's a 'start' point, then all edges should be 'outgoing',
            # i.e. we need to reverse the first segment's geometry. Otherwise,
            # it's an end coordinate and all edges should be 'incoming'.
            if point_type == 'start':
                edge1 = reverse_edge(edge1)
            else:
                edge2 = reverse_edge(edge2)

            # 4. Add initial costs
            # TODO: add a 'pretend' node? for cost fun params? Nodes are
            # currently ignored, for the cost function.
            result1['initial_cost'] = cost_fun(node1, node2, edge1)
            result2['initial_cost'] = cost_fun(node1, node2, edge2)

            # 5. Save the edge
            result1['initial_edge'] = edge1
            result2['initial_edge'] = edge2

            results = [result1, result2]

        return results

    origins = initialization_points(origin, point_type='start')
    destinations = initialization_points(destination, point_type='end')

    paths_data = []
    for o in origins:
        for d in destinations:
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
                total_cost, path = nx.single_source_dijkstra(G, o['node'],
                                                             d['node'],
                                                             weight=cost_fun)
            except nx.NetworkXNoPath:
                continue

            if 'initial_edge' in o:
                feature1 = edge_to_feature(o['initial_edge'],
                                           o['initial_cost'],
                                           False)
                path_data['features'].append(feature1)

            for node_id1, node_id2 in zip(path[:-1], path[1:]):
                node1 = G.nodes[node_id1]
                node2 = G.nodes[node_id2]
                edge = G[node_id1][node_id2]

                cost = cost_fun(node1, node2, edge)

                reverse = edge['from'] != node_id1

                feature = edge_to_feature(edge, cost, reverse)

                path_data['features'].append(feature)

            if 'initial_edge' in d:
                feature2 = edge_to_feature(d['initial_edge'],
                                           d['initial_cost'],
                                           False)
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

    # Start at first point
    coords = [best_path['features'][0]['geometry']['coordinates'][0]]
    segments = geojson.FeatureCollection([])
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
    route_response['destination'] = destination_feature
    route_response['waypoints'] = waypoints_feature_list
    route_response['routes'] = routes
    route_response['code'] = 'Ok'

    return route_response


def edge_to_feature(edge, cost, reverse=False):
    feature = geojson.Feature()

    if reverse:
        edge = reverse_edge(edge)
    else:
        edge = copy.copy(edge)

    feature['geometry'] = mapping(edge['geometry'])

    edge['cost'] = cost

    edge.pop('from')
    edge.pop('to')
    edge.pop('geometry')

    feature['properties'] = edge

    return feature


def reverse_edge(edge):
    new_edge = copy.copy(edge)
    coords = list(reversed(edge['geometry'].coords))
    new_edge['geometry'].coords = coords

    if 'incline' in new_edge:
        new_edge['incline'] = -1.0 * new_edge['incline']

    return new_edge
