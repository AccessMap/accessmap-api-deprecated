'''Functions to calculate travel costs originating at a given point. Can be
used to make things like isochrone maps.'''
import json
from accessmapapi import db


def travel_cost(lat, lon, costfun, table='routing', maxcost=1000):
    '''Given a lat, lon input and cost function (SQL string), calculate the
    time to travel out to a maximum cost value.'''

    # Find the origin point (a vertex on the routing vertices table)
    lonlat = 'ST_Setsrid(ST_Makepoint({}, {}), 4326)'.format(lon, lat)
    origin_sql = '''
      SELECT id
        FROM {}_vertices_pgr
    ORDER BY ST_Distance(the_geom, {})
       LIMIT 1;
    '''.format(table, lonlat)
    result = db.engine.execute(origin_sql)
    origin = result.fetchone()[0]
    result.close()

    travel_cost_sql = """
    SELECT seq,
           id1 AS node,
           cost,
           ST_AsGeoJSON(ST_Transform(nodes.the_geom, 4326)) AS geom
      FROM pgr_drivingDistance(
           'SELECT id,
                   source::int4,
                   target::int4,
                   {} AS cost
              FROM {}',
           {},
           {},
           false,
           false) pg
      JOIN {}_vertices_pgr nodes
        ON nodes.id = pg.id1
    """.format(costfun, table, origin, maxcost, table)
    fc = {'type': 'FeatureCollection',
          'features': []}
    result = db.engine.execute(travel_cost_sql)
    for row in result:
        cost = row[2]
        geom = json.loads(row[3])
        feature = {
            'type': 'Feature',
            'geometry': geom,
            'properties': {
                'cost': cost
            }
        }
        fc['features'].append(feature)
    result.close()

    return fc
