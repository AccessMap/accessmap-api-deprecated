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
    #
    # Strategy:
    # 1) Find nearest edge/node in table.
    # 2) If node, remember and use directly in routing later
    # 3) If edge, create new node at nearest point along with two new edges,
    #    one for each side of that point (e.g. middle of the block is closest?
    #    need to create path that goes one direct, one that goes the other).
    # 4) Put the edges in a new temporary table and re-derive its columns that
    #    get used in routing. Namely, barriers will need to be re-evaluated
    #    spatially - construction may only effect one of the new edges, e.g.
    # 5) Create temporary routing table view as union between original one and
    #    new temporary one that includes the two new vertices
    # 6) Create temporary routing vertex table view as union between original
    #    one and new temporary one (manually-created vertex table).
    # 7) Do routing on the views. The session closes after the routing query,
    #    and the temporary views + tables disappear.

    #
    # Find the nearest edge/node in the table
    #

    # Note: the units of the 'routing' table are WGS84, so the distance
    # calculation is not going to be correct (will involve lat degrees).
    nearest_sql = text('''
    CREATE TABLE partial AS
    SELECT ST_Line_Substring(geom, 0.0, frac) part1,
           ST_Line_Substring(geom, frac, 1.0) part2,
           ST_Line_Interpolate_Point(geom, frac) point,
           source,
           target,
           iscrossing,
           grade,
           curbramps,
           p2.idx
    FROM ((   SELECT r.geom,
                    ST_Line_Locate_Point(r.geom, p.point) frac,
                    r.source,
                    r.target,
                    r.iscrossing,
                    r.grade,
                    r.curbramps,
                    p.idx
               FROM routing r,
                    (SELECT ST_SetSRID(
                       ST_MakePoint(:lon1, :lat1),
                       4326
                     ) AS point,
                    1 AS idx
                    ) p
              WHERE r.iscrossing = 0
           ORDER BY geom <-> p.point
              LIMIT 1)
              UNION
          (  SELECT r.geom,
                    ST_Line_Locate_Point(r.geom, p.point) frac,
                    r.source,
                    r.target,
                    r.iscrossing,
                    r.grade,
                    r.curbramps,
                    p.idx
               FROM routing r,
                    (SELECT ST_SetSRID(
                       ST_MakePoint(:lon2, :lat2),
                       4326
                     ) AS point,
                    2 AS idx
                    ) p
              WHERE r.iscrossing = 0
           ORDER BY geom <-> p.point
              LIMIT 1)
         ) p2
    ORDER BY p2.idx
    ''')

    # Note: offset of -10 is to guarantee all temporary IDs are far away from
    # -1, which is used as a placeholder in the pgr_dijkstra result. Just in
    # case other negative numbers are used...
    temporary_nodes = text('''
    CREATE VIEW edges_vertices_pgr AS
    SELECT * FROM routing_vertices_pgr
     UNION (SELECT -1 * row_number() OVER () - 10 AS id,
                   NULL cnt,
                   NULL chk,
                   NULL ein,
                   NULL eout,
                   point the_geom
              FROM partial)
    ''')

    new_edges = text('''
    CREATE TABLE new_edges AS
    SELECT -1 * (2 * row_number() OVER ()) + 1 - 10 AS id,
           NULL o_id,
           part1 geom,
           grade,
           iscrossing,
           ST_Length(part1::geography) AS length,
           curbramps,
           source,
           -1 * row_number() OVER () - 10 AS target,
           FALSE construction
      FROM partial
     UNION
    SELECT -1 * (2 * row_number() OVER ()) - 10 AS id,
           NULL o_id,
           part2 geom,
           grade,
           iscrossing,
           ST_Length(part2::geography) AS length,
           curbramps,
           -1 * row_number() OVER () - 10 source,
           target,
           FALSE construction
      FROM partial
    ''')

    # Note: 'grade' value is kept because we don't have high enough resolution
    # (in most cases) to reliably do short distances. 'curbramps' value is
    # kept because it still implies the presence or basence of a curb ramp at
    # each end.

    # Fill in construction
    # FIXME: units are in degrees - about 10 cm in this case. No good!
    construction_sql = ('''
    UPDATE new_edges ne
       SET construction = TRUE
      FROM construction c
     WHERE ST_DWithin(ne.geom, c.geom, 0.000001)
    ''')

    temporary_edges = text('''
    CREATE VIEW edges AS
    SELECT id,
           geom,
           grade,
           length,
           iscrossing,
           curbramps,
           construction,
           source,
           target
      FROM routing
    UNION
    SELECT id,
           geom,
           grade,
           length,
           iscrossing,
           curbramps,
           construction,
           source,
           target
      FROM new_edges
    ''')

    ###########################################
    # With start/end nodes, get optimal route #
    ###########################################
    # node_start = 15307
    # node_end = 15308

    # Parameterize the cost function and get SQL back
    if cost_kwargs is None:
        cost_kwargs = {}
    cost_fun = cost(**cost_kwargs)

    # Note: Node IDs 11 and 12 are hard-coded, will need to be replaced if
    # more than 2 waypoints are ever needed
    output_sql = text('''
    SELECT CASE t.source
           WHEN (p.pgr).id1
           THEN ST_AsGeoJSON(t.geom, 7)
           ELSE ST_AsGeoJSON(ST_Reverse(t.geom), 7)
            END
             AS geom,
                (p.pgr).cost,
                t.grade,
                t.construction,
                (p.pgr).seq,
                (p.pgr).id1,
                (p.pgr).id2
      FROM edges t
      JOIN (SELECT pgr_dijkstra('SELECT id::integer,
                                        source::integer,
                                        target::integer,
                                        {cost}::double precision AS cost
                                   FROM edges',
                                -11,
                                -12,
                                false,
                                false) AS pgr
            ) p
        ON id = (p.pgr).id2
    ORDER BY (p.pgr).seq
    '''.format(cost=cost_fun))

    with db.engine.connect() as conn:
        with conn.begin() as trans:
            try:
                conn.execute(nearest_sql, lon1=origin[1], lat1=origin[0],
                             lon2=destination[1], lat2=destination[0])
                conn.execute(temporary_nodes)
                conn.execute(new_edges)
                conn.execute(construction_sql)
                conn.execute(temporary_edges)
                result = conn.execute(output_sql)
                trans.commit()
            except:
                trans.rollback()
                raise
            finally:
                # FIXME: this shouldn't happen if each connection launched a
                # new session (i.e. temporary table should be non-shared).
                # But if this line is removed, subsequent queries find the
                # 'partial' table. Why?
                conn.execute('DROP TABLE IF EXISTS partial CASCADE')
                conn.execute('DROP TABLE IF EXISTS new_edges CASCADE')
                pass

    route_rows = list(result)
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
