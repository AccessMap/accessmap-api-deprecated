from . import db
import json


def routing_request(waypoints):
    '''Process a routing request, returning a Mapbox-compatible routing JSON
    object.

    :param waypoints: list of coordinates for start, stop locations
    :type waypoints: list of lists of coordinates

    '''
    kdist = 1.0
    kele = 1e10
    routing_table = 'routing'
    # Isolate first and last points
    origin = waypoints.pop(0)
    dest = waypoints.pop()
    # Find sidewalks closest to origin and destination ###
    routing_vertices_table = routing_table + '_vertices_pgr'

    # BIG FIXME: WOW, these aren't injection safe at all (Bobby Tables...)
    point_sql = 'ST_SetSRID(ST_Makepoint({}, {}), 4326)'
    # Note that in geoJSON, the order is [lon, lat], so reversed order here
    origin_geom = point_sql.format(origin[1], origin[0])
    dest_geom = point_sql.format(dest[1], dest[0])

    # FIXME: The closest node to the selected point is not actually what we
    # want - that ends up with weird backtracking scenarios. What we want is
    # something like a new virtual node on the closest edge - i.e. the closest
    # realistic start point in the real world. I haven't been able to find a
    # pre-built solution for this in pgRouting. pgr_trsp can start and end at
    # edges + a distance along that edge, but it may not work easily with
    # custom cost functions (verify that). We can also roll our own option.
    # It will add some complication, as we'll need to calculate costs for the
    # two virtual edges of our virtual node. To do that super accurately, we'd
    # need to go back to the functions used to label data and apply them again
    # or approximate new costs (or attributes) on the virtual edges.
    # FIXME: Once closest-edge selection is implemented, remember to include
    # sidewalk edges and corners and disclude crossing edges.
    closest_row_sql = '''  SELECT id
                             FROM {}
                         ORDER BY ST_Distance(the_geom, {})
                            LIMIT 1;'''
    origin_query = closest_row_sql.format(routing_vertices_table, origin_geom)
    dest_query = closest_row_sql.format(routing_vertices_table, dest_geom)

    result = db.engine.execute(origin_query)
    start_node = list(result)[0][0]
    result.close()

    result = db.engine.execute(dest_query)
    end_node = list(result)[0][0]
    result.close()

    # Cost function and routing
    # FIXME: these costs need to be normalized (distance vs. elevation)

    # Cost function(s)
    # cost_fun = 'ST_length(geom) + (k_ele * abs(geom.ele1 - geom.ele2))'
    dist_cost = '{} * ST_length(geom::geography)'.format(kdist)
    # height_cost = '{} * ABS(ele_change)'.format(kele)
    # Instead, let's do a slope cost
    slope_cost = ('CASE ST_length(geom) WHEN 0 THEN 0 ELSE '
                  '{} * POW(ABS(ele_change) / ST_length(geom::geography), 4)'
                  'END')
    slope_cost = slope_cost.format(kele)
    kcrossing = 1e2
    crossing_cost = '{} * iscrossing'.format(kcrossing)
    cost_fun = ' + '.join([dist_cost, slope_cost, crossing_cost])

    ###########################################
    # With start/end nodes, get optimal route #
    ###########################################
    # node_start = 15307
    # node_end = 15308
    # Origin and Destination nodes in pgRouting vertex table
    pgr_sql = '''SELECT id,
                        source::integer,
                        target::integer,
                        {}::double precision AS cost
                   FROM {};'''.format(cost_fun, routing_table)
    # Request route - turn geometries directly into GeoJSON
    route_sql = '''SELECT seq,
                          id1::integer AS node,
                          id2::integer AS edge,
                          cost
                     FROM pgr_dijkstra('{}',{},{},{},{});'''
    route_query = route_sql.format(pgr_sql, start_node, end_node, 'false',
                                   'false', routing_table)
    result = db.engine.execute(route_query)
    rows = list(result)
    result.close()

    geom_fc = {'type': 'FeatureCollection',
               'features': []}
    geoms = []
    for row in rows:
        node_id = row[1]
        edge_id = row[2]

        if edge_id != -1:
            geom_query = '''
                SELECT ST_AsGeoJSON(geom, 7),
                       ST_AsText(geom)
                  FROM {}
                 WHERE source = {} AND id = {}
                 UNION
                SELECT ST_AsGeoJSON(ST_Reverse(geom), 7),
                       ST_AsText(ST_Reverse(geom))
                  FROM {}
                 WHERE target = {} AND id = {};
            '''.format(routing_table, node_id, edge_id, routing_table,
                       node_id, edge_id)
            result = db.engine.execute(geom_query)
            result_list = list(result)
            if not result_list:
                return {'code': 'NoRoute',
                        'waypoints': [],
                        'routes': []}
            geom_row = result_list[0]
            result.close()
            feature = {'type': 'Feature',
                       'geometry': json.loads(geom_row[0]),
                       'properties': {}}
            geom_fc['features'].append(feature)
            geom = 'ST_GeomFromText(\'{}\')'.format(geom_row[1])
            geoms.append(geom)

    print(geom_fc)
    geom_array_args = ', '.join(geoms)

    # Take geoms and join them into one big linestring
    merge_query = '''
        SELECT ST_AsGeoJSON(ST_LineMerge(ST_Union(ST_Collect(ARRAY[{}]))), 7);
    '''.format(geom_array_args)
    result = db.engine.execute(merge_query)
    coords = json.loads(list(result)[0][0])['coordinates']
    result.close()

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
                      'geometry': {'type': 'Point',
                                   'coordinates': [origin[1], origin[0]]},
                      'properties': {}}

    dest_feature = {'type': 'Feature',
                    'geometry': {'type': 'Point',
                                 'coordinates': [dest[1], dest[0]]},
                    'properties': {}}
    waypoints_feature_list = []
    for waypoint in waypoints:
        waypoint_feature = {'type': 'Feature',
                            'geometry': {'type': 'Point',
                                         'coordinates': waypoint},
                            'properties': {}}
        waypoints_feature_list.append(waypoint_feature)

    # TODO: here's where to add alternative routes once we have them
    routes = []
    route = {}
    route['geometry'] = {'type': 'LineString',
                         'coordinates': []}
    # Route geometries look like [coord1, coord2], if we just concatenated then
    # coord2 from the first geometry is coord1 from the second - gotta exclude
    # the first one after the initial
    # FIXME: prepended and appended waypoints to fix bug - shouldn't
    #        pgrouting return them as part of the steps?
    # Origin coordinates (start)
    route['geometry']['coordinates'].append([origin[1], origin[0]])
    # Route coordinates
    route['geometry']['coordinates'] += coords
    # for geom in route_geoms:
    #     # FIXME: this isn't quite what we want (likely has redundant points)
    #     #        instead, generate polyline in the SQL command
    #     for coord in geom['coordinates']:
    #         route['geometry']['coordinates'].append(coord)
    # Destination coordinates (end)
    route['geometry']['coordinates'].append([dest[1], dest[0]])

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
