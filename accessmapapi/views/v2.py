from accessmapapi import app, db, models, sql_utils
from accessmapapi.routing import costs, route, travelcost
from flask import jsonify, request
import geoalchemy2.functions as gfunc
import geojson
import json


@app.route('/v2/sidewalks.geojson')
def sidewalksv2():
    table = models.Sidewalks
    bbox = request.args.get('bbox')
    all_rows = request.args.get('all')
    geojson_query = gfunc.ST_AsGeoJSON(table.geog, 8)
    geojson_geog = geojson_query.label('geog')
    if all_rows == 'true':
        select = db.session.query(table.id,
                                  geojson_geog,
                                  table.incline)
        result = select.all()
    else:
        if not bbox:
            select = db.session.query(table.id,
                                      geojson_geog,
                                      table.incline)
            result = select.limit(10).all()
        else:
            bounds = [float(b) for b in bbox.split(',')]
            in_bbox = sql_utils.in_bbox(table.geog, bounds)
            select = db.session.query(table.id,
                                      geojson_geog,
                                      table.incline)
            result = select.filter(in_bbox).all()

    feature_collection = geojson.FeatureCollection([])
    for row in result:
        feature = geojson.Feature()
        geometry = json.loads(row.geog)
        feature['geometry'] = geometry
        feature['properties'] = {'id': row.id,
                                 'incline': str(round(row.incline, 3))}
        feature_collection['features'].append(feature)

    return jsonify(feature_collection)


@app.route('/v2/crossings.geojson')
def crossingsv2():
    table = models.Crossings
    bbox = request.args.get('bbox')
    all_rows = request.args.get('all')
    geojson_query = gfunc.ST_AsGeoJSON(table.geog, 8)
    geojson_geog = geojson_query.label('geog')
    if all_rows == 'true':
        select = db.session.query(table.id,
                                  geojson_geog,
                                  table.incline,
                                  table.curbramps)
        result = select.all()
    else:
        if not bbox:
            select = db.session.query(table.id,
                                      geojson_geog,
                                      table.incline,
                                      table.curbramps)
            result = select.limit(10).all()
        else:
            bounds = [float(b) for b in bbox.split(',')]
            in_bbox = sql_utils.in_bbox(table.geog, bounds)
            select = db.session.query(table.id,
                                      geojson_geog,
                                      table.incline,
                                      table.curbramps)
            result = select.filter(in_bbox).all()

    fc = geojson.FeatureCollection([])
    for row in result:
        feature = geojson.Feature()
        geometry = json.loads(row.geog)
        for i, lonlat in enumerate(geometry['coordinates']):
            lon = round(lonlat[0], 7)
            lat = round(lonlat[1], 7)
            geometry['coordinates'][i] = [lon, lat]
        feature['geometry'] = geometry
        feature['properties'] = {'id': row.id,
                                 'incline': str(round(row.incline, 3)),
                                 'curbramps': row.curbramps}
        fc['features'].append(feature)

    return jsonify(fc)


@app.route('/v2/route.json', methods=['GET'])
def routev2():
    # Test coordinates:
    #   origin: 47.655883 -122.311994
    #   destination: 47.659877,-122.316052
    origin = request.args.get('origin', None)
    destination = request.args.get('destination', None)
    if (origin is None) or (destination is None):
        # TODO: return status code 400
        return jsonify({
            'status': 'BadInput',
            'errmessage': 'origin and destination parameters are required.'
        })

    # request route
    params = ['avoid', 'maxdown', 'ideal', 'maxup']
    cost_params = {
        'avoid_curbs': False,
        'avoid_construction': False
    }
    for param in params:
        value = request.args.get(param, None)
        if value is not None:
            if param == 'avoid':
                # Process barriers - pipe-separated e.g. curbs|construction
                barriers = value.split('|')
                if 'curbs' in barriers:
                    cost_params['avoid_curbs'] = True
                if 'construction' in barriers:
                    cost_params['avoid_construction'] = True
            else:
                cost_params[param] = value

    origin_coords = origin.split(',')
    dest_coords = destination.split(',')

    route_response = route.routing_request(origin_coords, dest_coords,
                                           cost=costs.manual_wheelchair,
                                           cost_kwargs=cost_params)

    return jsonify(route_response)


@app.route('/v2/travelcost.json', methods=['GET'])
def travelcostv2():
    # Process arguments
    # TODO: input validation - return reasonable HTTP errors on bad input.
    # latlon (required!)
    lat = request.args.get('lat', None)
    lon = request.args.get('lon', None)
    if lat is None or lon is None:
        return 'Bad request - lat and lon parameters are required.'

    # Calculate travel time
    costfun = costs.manual_wheelchair()
    cost_points = travelcost.travel_cost(lat, lon, costfun, maxcost=10000)

    return jsonify(cost_points)
