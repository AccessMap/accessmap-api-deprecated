from FlaskWebProject import app, db, models, sql_utils, routing
from flask import request
import geoalchemy2.functions as gfunc
# import geoalchemy2 as ga
import geojson
import json


@app.route('/v2/sidewalks.geojson')
def sidewalksv2():
    table = models.Sidewalks
    bbox = request.args.get('bbox')
    geojson_query = gfunc.ST_AsGeoJSON(gfunc.ST_Transform(table.geom, 4326))
    geojson_geom = geojson_query.label('geom')
    if not bbox:
        select = db.session.query(table.id,
                                  geojson_geom,
                                  table.grade)
        result = select.limit(10).all()
    else:
        bounds = [float(b) for b in bbox.split(',')]
        in_bbox = sql_utils.in_bbox(table.geom, bounds)
        select = db.session.query(table.id,
                                  geojson_geom,
                                  table.grade)
        result = select.filter(in_bbox).all()

    fc = geojson.FeatureCollection([])
    for row in result:
        feature = geojson.Feature()
        feature['geometry'] = json.loads(row.geom)
        feature['properties'] = {'id': row.id,
                                 'grade': row.grade}
        fc['features'].append(feature)

    return json.dumps(fc)


@app.route('/v2/crossings.geojson')
def crossingsv2():
    table = models.Crossings
    bbox = request.args.get('bbox')
    geojson_query = gfunc.ST_AsGeoJSON(gfunc.ST_Transform(table.geom, 4326))
    geojson_geom = geojson_query.label('geom')
    if not bbox:
        select = db.session.query(table.id,
                                  geojson_geom,
                                  table.grade)
        result = select.limit(10).all()
    else:
        bounds = [float(b) for b in bbox.split(',')]
        in_bbox = sql_utils.in_bbox(table.geom, bounds)
        select = db.session.query(table.id,
                                  geojson_geom,
                                  table.grade)
        result = select.filter(in_bbox).all()

    fc = geojson.FeatureCollection([])
    for row in result:
        feature = geojson.Feature()
        feature['geometry'] = json.loads(row.geom)
        feature['properties'] = {'id': row.id,
                                 'grade': row.grade}
        fc['features'].append(feature)

    return json.dumps(fc)


@app.route('/v2/route.json', methods=['GET'])
def routev2():
    # Process arguments
    # TODO: input validation - return reasonable HTTP errors on bad input.
    # latlon (required!)
    waypoints_input = request.args.get('waypoints', None)
    if waypoints_input is None:
        return 'Bad request - waypoints parameter is required.'
    waypoints_input_list = json.loads(waypoints_input)
    # Consume in pairs
    waypoints = zip(waypoints_input_list[0::2], waypoints_input_list[1::2])

    # request route
    route_response = routing.routing_request(list(waypoints))

    return json.dumps(route_response)


@app.route('/v2/mapinfo')
def mapinfov2():
    info = {'tiles': app.config['MAPBOX_TILES'],
            'token': app.config['MAPBOX_TOKEN']}

    return json.dumps(info)
