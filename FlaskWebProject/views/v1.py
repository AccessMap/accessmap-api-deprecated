from FlaskWebProject import app, db, models, sql_utils
from flask import jsonify, request
import geoalchemy2.functions as gfunc
# import geoalchemy2 as ga
import geojson
import json


@app.route('/v1/sidewalks.geojson')
def sidewalksv1():
    table = models.SidewalksData
    bbox = request.args.get('bbox')
    geom_latlon = gfunc.ST_Transform(table.geom, 4326)
    geojson_query = gfunc.ST_AsGeoJSON(geom_latlon)
    geojson_geom = geojson_query.label('geom')
    if not bbox:
        select = db.session.query(table.id,
                                  geojson_geom,
                                  table.grade)
        result = select.limit(10).all()
    else:
        bounds = [float(b) for b in bbox.split(',')]
        in_bbox = sql_utils.in_bbox(geom_latlon, bounds)
        select = db.session.query(table.id,
                                  geojson_geom,
                                  table.grade)
        result = select.filter(in_bbox).all()

    feature_collection = geojson.FeatureCollection([])
    for row in result:
        feature = geojson.Feature()
        # Trim to 7 decimal places to decrease amount of data sent
        # (corresponds to about 11 mm precision)
        geometry = json.loads(row.geom)
        for i, lonlat in enumerate(geometry['coordinates']):
            lon = round(lonlat[0], 7)
            lat = round(lonlat[1], 7)
            geometry['coordinates'][i] = [lon, lat]

        feature['geometry'] = geometry
        feature['properties'] = {'id': row.id,
                                 'grade': round(row.grade, 3)}
        feature_collection['features'].append(feature)

    return jsonify(feature_collection)


@app.route('/v1/curbramps.geojson')
def curbrampsv1():
    table = models.CurbrampsData
    bbox = request.args.get('bbox')
    geom_latlon = gfunc.ST_Transform(table.geom, 4326)
    geojson_query = gfunc.ST_AsGeoJSON(geom_latlon)
    geojson_geom = geojson_query.label('geom')
    if not bbox:
        select = db.session.query(table.id,
                                  geojson_geom)
        result = select.limit(10).all()
    else:
        bounds = [float(b) for b in bbox.split(',')]
        in_bbox = sql_utils.in_bbox(geom_latlon, bounds)
        select = db.session.query(table.id,
                                  geojson_geom)
        result = select.filter(in_bbox).all()

    fc = geojson.FeatureCollection([])
    for row in result:
        feature = geojson.Feature()
        feature['geometry'] = json.loads(row.geom)
        feature['properties'] = {'id': row.id}
        fc['features'].append(feature)

    return jsonify(fc)


@app.route('/v1/mapinfo')
def mapinfov1():
    info = {'tiles': app.config['MAPBOX_TILES'],
            'token': app.config['MAPBOX_TOKEN']}

    return jsonify(info)
