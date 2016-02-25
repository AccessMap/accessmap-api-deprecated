from FlaskWebProject import app, db, models, sql_utils
from flask import request
import geoalchemy2.functions as gfunc
# import geoalchemy2 as ga
import geojson
import json


@app.route('/v1/sidewalks.geojson')
def sidewalksv1():
    table = models.SidewalksData
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


@app.route('/v1/curbramps.geojson')
def curbrampsv1():
    table = models.CurbrampsData
    bbox = request.args.get('bbox')
    geojson_query = gfunc.ST_AsGeoJSON(gfunc.ST_Transform(table.geom, 4326))
    geojson_geom = geojson_query.label('geom')
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

    fc = geojson.FeatureCollection([])
    for row in result:
        feature = geojson.Feature()
        feature['geometry'] = json.loads(row.geom)
        feature['properties'] = {'id': row.id}
        fc['features'].append(feature)

    return json.dumps(fc)


@app.route('/v1/mapinfo')
def mapinfov1():
    info = {'tiles': app.config['MAPBOX_TILES'],
            'token': app.config['MAPBOX_TOKEN']}

    return json.dumps(info)
