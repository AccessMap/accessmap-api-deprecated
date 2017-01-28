from accessmapapi import db
from sqlalchemy.sql import text
from . import costs
import json


def routing_request(origin, destination, cost=costs.manual_wheelchair,
                    cost_kwargs=None, table='routing'):
    '''Process a routing request, returning a Mapbox-compatible routing JSON
    object.

    :param origin: lat-lon of starting location.
    :type origin: list of coordinates
    :param destination: lat-lon of ending location.
    :type destination: list of coordinates
    :param cost: SQL-rendering cost function to use
    :type cost: callable
    :param cost_kwargs: keyword arguments to pass to the cost function.
    :type cost_kwargs: dict

    '''

    # FIXME: We should find the closest point (a sidewalk vertex or
    #        mid-sidewalk, e.g. This requires dynamically adding nodes + edges
    #        + costs to the table for each request.

    ###########################################
    # With start/end nodes, get optimal route #
    ###########################################
    # node_start = 15307
    # node_end = 15308

    # Parameterize the cost function and get SQL back
    if cost_kwargs is None:
        cost_kwargs = {}
    cost_fun = cost(**cost_kwargs)

    output_sql = text('''
    SELECT CASE source
           WHEN (p.pgr).id1
           THEN ST_AsGeoJSON(t.geom, 7)
           ELSE ST_AsGeoJSON(ST_Reverse(t.geom), 7)
            END
             AS geom,
                (p.pgr).cost,
                t.grade,
                t.construction
      FROM {table} t
      JOIN (SELECT pgr_dijkstra('SELECT id::integer,
                                        source::integer,
                                        target::integer,
                                        {cost}::double precision AS cost
                                   FROM {table}',
                                node1.id,
                                node2.id,
                                :directed,
                                :rcost) AS pgr
              FROM (  SELECT id
                        FROM {table}_vertices_pgr
                    ORDER BY ST_Distance(the_geom,
                                         ST_SetSRID(
                                            ST_Makepoint(:lon1, :lat1),
                                            4326))
                       LIMIT 1) node1,
                   (  SELECT id
                        FROM {table}_vertices_pgr
                    ORDER BY ST_Distance(the_geom,
                                         ST_SetSRID(
                                            ST_Makepoint(:lon2, :lat2),
                                            4326))
                       LIMIT 1) node2
            ) p
        ON id = (p.pgr).id2
    '''.format(table=table, cost=cost_fun))

    result = db.engine.execute(output_sql, lon1=origin[1], lat1=origin[0],
                               lon2=destination[1], lat2=destination[0],
                               directed='false', rcost='false')

    route_rows = list(result)
    result.close()
    if not route_rows:
        return {'code': 'NoRoute',
                'waypoints': [],
                'routes': []}

    segments = {
        'type': 'FeatureCollection',
        'features': []
    }
    coords = []
    for row in route_rows:
        geometry = json.loads(row[0])
        segment = {
            'type': 'Feature',
            'geometry': geometry,
            'properties': {
                'cost': row[1],
                'grade': float(row[2]),
                'construction': bool(row[3])
            }
        }
        segments['features'].append(segment)

        coords += geometry['coordinates']

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
                                 'coordinates': [destination[1],
                                                 destination[0]]},
                    'properties': {}}
    waypoints_feature_list = []
    for waypoint in [origin, destination]:
        waypoint_feature = {'type': 'Feature',
                            'geometry': {'type': 'Point',
                                         'coordinates': waypoint},
                            'properties': {}}
        waypoints_feature_list.append(waypoint_feature)

    # TODO: here's where to add alternative routes once we have them
    routes = []
    route = {}
    route['geometry'] = {'type': 'LineString',
                         'coordinates': coords}

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
