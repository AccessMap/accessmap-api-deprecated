from flask_restful import Resource, reqparse
import geojson

from app import database as db
from app.sql_utils import bbox_filter


# Default query limit if no params are offered
N_RESULTS_DEFAULT = 30


parser = reqparse.RequestParser()
# I think it's a string? [lon1,lat1,lon2,lat2]
parser.add_argument('bbox', type=str)


class SidewalksV1(Resource):
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
            props = {'id': row.id,
                     'grade': row.grade}
            sidewalk = geojson.Feature(geometry=geom, properties=props)

            sidewalks.append(sidewalk)

        sidewalks_fc = geojson.FeatureCollection(sidewalks)
        return sidewalks_fc
