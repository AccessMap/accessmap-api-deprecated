from accessmapapi import app, db, models, sql_utils, routing
from flask import jsonify, request
import geoalchemy2.functions as gfunc
# import geoalchemy2 as ga
import geojson
import json


@app.route('/v2/sidewalks.geojson')
def sidewalksv2():
    table = models.Sidewalks
    bbox = request.args.get('bbox')
    all_rows = request.args.get('all')
    geojson_query = gfunc.ST_AsGeoJSON(table.geom, 7)
    geojson_geom = geojson_query.label('geom')
    if all_rows == 'true':
        select = db.session.query(table.id,
                                  geojson_geom,
                                  table.grade)
        result = select.all()
    else:
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

    feature_collection = geojson.FeatureCollection([])
    for row in result:
        feature = geojson.Feature()
        geometry = json.loads(row.geom)
        feature['geometry'] = geometry
        feature['properties'] = {'id': row.id,
                                 'grade': round(row.grade, 3)}
        feature_collection['features'].append(feature)

    return jsonify(feature_collection)


@app.route('/v2/crossings.geojson')
def crossingsv2():
    table = models.Crossings
    bbox = request.args.get('bbox')
    all_rows = request.args.get('all')
    geojson_query = gfunc.ST_AsGeoJSON(table.geom, 7)
    geojson_geom = geojson_query.label('geom')
    if all_rows == 'true':
        select = db.session.query(table.id,
                                  geojson_geom,
                                  table.grade,
                                  table.curbramps)
        result = select.all()
    else:
        if not bbox:
            select = db.session.query(table.id,
                                      geojson_geom,
                                      table.grade,
                                      table.curbramps)
            result = select.limit(10).all()
        else:
            bounds = [float(b) for b in bbox.split(',')]
            in_bbox = sql_utils.in_bbox(table.geom, bounds)
            select = db.session.query(table.id,
                                      geojson_geom,
                                      table.grade,
                                      table.curbramps)
            result = select.filter(in_bbox).all()

    fc = geojson.FeatureCollection([])
    for row in result:
        feature = geojson.Feature()
        geometry = json.loads(row.geom)
        for i, lonlat in enumerate(geometry['coordinates']):
            lon = round(lonlat[0], 7)
            lat = round(lonlat[1], 7)
            geometry['coordinates'][i] = [lon, lat]
        feature['geometry'] = geometry
        feature['properties'] = {'id': row.id,
                                 'grade': round(row.grade, 3),
                                 'curbramps': row.curbramps}
        fc['features'].append(feature)

    return jsonify(fc)


@app.route('/v2/curbramps.geojson')
def curbrampsv2():
    table = models.Curbramps
    bbox = request.args.get('bbox')
    all_rows = request.args.get('all')
    geojson_query = gfunc.ST_AsGeoJSON(table.geom, 7)
    geojson_geom = geojson_query.label('geom')
    if all_rows == 'true':
        select = db.session.query(table.id,
                                  geojson_geom)
        result = select.all()
    else:
        if not bbox:
            select = db.session.query(table.id,
                                      geojson_geom)
            result = select.limit(10).all()
        else:
            bounds = [float(b) for b in bbox.split(',')]
            in_bbox = sql_utils.in_bbox(table.geom, bounds)
            select = db.session.query(table.id,
                                      geojson_geom)
            result = select.filter(in_bbox).all()

    feature_collection = geojson.FeatureCollection([])
    for row in result:
        feature = geojson.Feature()
        geometry = json.loads(row.geom)
        feature['geometry'] = geometry
        feature['properties'] = {'id': row.id}
        feature_collection['features'].append(feature)

    return jsonify(feature_collection)


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

    return jsonify(route_response)
