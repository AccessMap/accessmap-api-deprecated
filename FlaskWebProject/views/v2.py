from FlaskWebProject import app, db, models, sql_utils, isochrones
from flask import request
import geoalchemy2.functions as gfunc
# import geoalchemy2 as ga
import geojson
import json


@app.route('/v2/sidewalks.geojson')
def sidewalksv2():
    table = models.Sidewalks
    bbox = request.args.get('bbox')
    geojson_geom = gfunc.ST_AsGeoJSON(table.geom).label('geom')
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
    table = models.Sidewalks
    bbox = request.args.get('bbox')
    geojson_geom = gfunc.ST_AsGeoJSON(table.geom).label('geom')
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


@app.route('/v2/isochrone.geojson')
def isochronev2():
    lon = float(request.args.get('lon'))
    lat = float(request.args.get('lat'))
    if lon is None or lat is None:
        return 'Bad request - lon and lat parameters are required.'
    wcorridors = request.args.get('wcorridors')

    if wcorridors == 'true':
        isochrone = isochrones.get_isochrone([lon, lat])
    else:
        isochrone = isochrones.get_isochrone([lon, lat], 'costnocorridors')

    return json.dumps(isochrone)