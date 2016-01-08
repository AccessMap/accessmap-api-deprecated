from flask_restful import Resource, reqparse
import geojson

from app import database as db
from app.sql_utils import bbox_filter


# Default query limit if no params are offered
N_RESULTS_DEFAULT = 30


parser = reqparse.RequestParser()
# I think it's a string? [lon1,lat1,lon2,lat2]
parser.add_argument('bbox', type=str)


class CurbrampsV1(Resource):
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
            props = {'id': row.id}
            curb = geojson.Feature(geometry=geom, properties=props)
            curbs.append(curb)

        curbs_fc = geojson.FeatureCollection(curbs)
        return curbs_fc
