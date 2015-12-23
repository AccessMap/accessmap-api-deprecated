from flask_restful import Api, Resource, reqparse
import geojson
from shapely import geometry

from .models import Curb, Permit, SidewalkGrade
from . import db
from . import app


api = Api(app)

# Default query limit if no params are offered
N_RESULTS_DEFAULT = 100


parser = reqparse.RequestParser()
# I think it's a string? [lon1,lat1,lon2,lat2]
parser.add_argument("bbox", type=str)

# TODO: The classes below have a lot of redundancies - we should eventually
# use something like factories for our geoJSON exchange functionality


class CurbsAPI(Resource):
    def get(self):
        args = parser.parse_args()
        if args['bbox']:
            bbox = [float(point) for point in args["bbox"].split(",")]
            query = bbox_filter(Curb, bbox)
        else:
            query = Curb.query.limit(N_RESULTS_DEFAULT)

        curb_list = []
        for row in query:
            geom = geojson.loads(db.session.scalar(row.geom.ST_AsGeoJSON()))
            props = {"sidewalk_objectid": row.sidewalk_objectid,
                     "angle": row.angle}
            curb = geojson.Feature(geometry=geom, properties=props)
            curb_list.append(curb)

        curb_fc = geojson.FeatureCollection(curb_list)
        return curb_fc


class PermitsAPI(Resource):
    def get(self):
        args = parser.parse_args()
        if args['bbox']:
            bbox = [float(point) for point in args["bbox"].split(",")]
            query = bbox_filter(Permit, bbox)
        else:
            query = Permit.query.limit(N_RESULTS_DEFAULT)

        permits_list = []
        for row in query:
            geom = geojson.loads(db.session.scalar(row.geom.ST_AsGeoJSON()))
            props = {"objectid": row.objectid,
                     "permit_no": row.permit_no,
                     "mobility_impact_text": row.mobility_impact_text,
                     "permit_address_text": row.permit_address_text,
                     "applicant_name": row.applicant_name}
            permit = geojson.Feature(geometry=geom, properties=props)
            permits_list.append(permit)

        permits_fc = geojson.FeatureCollection(permits_list)
        return permits_fc


class SidewalkGradesAPI(Resource):
    def get(self):
        args = parser.parse_args()
        if args['bbox']:
            bbox = [float(point) for point in args["bbox"].split(",")]
            query = bbox_filter(SidewalkGrade, bbox)
        else:
            query = SidewalkGrade.query.limit(N_RESULTS_DEFAULT)

        sidewalk_grades_list = []
        for row in query:
            geom = geojson.loads(db.session.scalar(row.geom.ST_AsGeoJSON()))
            props = {"sidewalk_objectid": row.sidewalk_objectid,
                     "grade": row.grade}
            sidewalk_grade = geojson.Feature(geometry=geom, properties=props)

            sidewalk_grades_list.append(sidewalk_grade)

        sidewalk_grades_fc = geojson.FeatureCollection(sidewalk_grades_list)
        return sidewalk_grades_fc


def bbox_filter(table, bbox):
    """Table is actual table object, bbox is of the form
    [lon1, lat1, lon2, lat2]

    Returns rows as a list

    """
    # TODO: Make this faster
    # Generate the polygon for the bounding box
    coords = [[bbox[0], bbox[1]], [bbox[0], bbox[3]], [bbox[2], bbox[3]],
              [bbox[2], bbox[1]], [bbox[0], bbox[1]]]
    box = geometry.Polygon(coords)

    filtered = table.query.filter(table.geom.intersects(box.to_wkt()))

    return list(filtered)


@app.route("/")
def index():
    return "Hackcessible API site - access is secret!"


api.add_resource(CurbsAPI, "/raw-curbs.geojson")
api.add_resource(PermitsAPI, "/raw-permits.geojson")
api.add_resource(SidewalkGradesAPI, "/raw-sidewalks.geojson")
