from decimal import Decimal
from flask_restful import Api, Resource, reqparse
import geojson
from shapely import geometry

from . import database as db
from . import app


api = Api(app)

# Default query limit if no params are offered
N_RESULTS_DEFAULT = 100


parser = reqparse.RequestParser()
# I think it's a string? [lon1,lat1,lon2,lat2]
parser.add_argument('bbox', type=str)

# TODO: The classes below have a lot of redundancies - we should eventually
# use something like factories for our geoJSON exchange functionality


class CurbsAPI(Resource):
    def get(self):
        args = parser.parse_args()
        if args['bbox']:
            bbox = [float(point) for point in args['bbox'].split(',')]
            query = bbox_filter(db.curbramps_data, bbox)
        else:
            query = db.curbramps_data.select().limit(N_RESULTS_DEFAULT)

        executed = db.engine.execute(query)
        curbs = []
        for row in executed:
            raw_geojson = db.engine.execute(row.geom.ST_AsGeoJSON()).fetchone()
            geom = geojson.loads(raw_geojson[0])
            props = {'id': int(row.id)}
            curb = geojson.Feature(geometry=geom, properties=props)
            curbs.append(curb)

        curbs_fc = geojson.FeatureCollection(curbs)
        return curbs_fc


class SidewalkGradesAPI(Resource):
    def get(self):
        args = parser.parse_args()
        if args['bbox']:
            bbox = [float(point) for point in args['bbox'].split(',')]
            query = bbox_filter(db.sidewalks_data, bbox)
        else:
            query = db.sidewalks_data.select().limit(N_RESULTS_DEFAULT)

        executed = db.engine.execute(query)
        sidewalks = []
        for row in executed:
            row_query = row.geom.ST_AsGeoJSON()
            raw_geojson = db.engine.execute(row_query).fetchone()
            geom = geojson.loads(raw_geojson[0])
            grade = row.grade.quantize(Decimal('.0001'))
            props = {'id': row.id,
                     'grade': float(grade)}
            sidewalk = geojson.Feature(geometry=geom, properties=props)

            sidewalks.append(sidewalk)
        print row_query

        sidewalks_fc = geojson.FeatureCollection(sidewalks)
        return sidewalks_fc


def bbox_filter(table, bbox):
    '''Table is actual table object, bbox is of the form
    [lon1, lat1, lon2, lat2]

    Returns rows as a list

    '''
    # TODO: Make this faster
    # Generate the polygon for the bounding box
    coords = [[bbox[0], bbox[1]], [bbox[0], bbox[3]], [bbox[2], bbox[3]],
              [bbox[2], bbox[1]], [bbox[0], bbox[1]]]
    box = geometry.Polygon(coords)

    filtered = table.select().where(table.geom.intersects(box.to_wkt()))

    return filtered


@app.route('/')
def index():
    return 'Hackcessible API site - access is secret!'


api.add_resource(CurbsAPI, '/curbramps-data.geojson')
api.add_resource(SidewalkGradesAPI, '/sidewalks-data.geojson')
