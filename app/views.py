from flask_restful import Api, Resource, reqparse
from geomet import wkt

from .models import Curb, Permit, SidewalkElevation
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
            results = bbox_filter(Curb, bbox)
        else:
            results = Curb.query.limit(N_RESULTS_DEFAULT)
        jsoned = []
        for row in results:
            geom = wkt.loads(db.session.scalar(row.coordinates.wkt))
            result_dict = {
                "type": geom["type"],
                "coordinates": geom["coordinates"],
                "properties": {
                    "sidewalk_objectid": row.sidewalk_objectid,
                    "angle": row.angle
                }
            }
            jsoned.append(result_dict)
        return jsoned


class PermitsAPI(Resource):
    def get(self):
        args = parser.parse_args()
        if args['bbox']:
            bbox = [float(point) for point in args["bbox"].split(",")]
            results = bbox_filter(Permit, bbox)
        else:
            results = Permit.query.limit(N_RESULTS_DEFAULT)
        jsoned = []
        for row in results:
            geom = wkt.loads(db.session.scalar(row.coordinates.wkt))
            result_dict = {
                "type": geom["type"],
                "coordinates": geom["coordinates"],
                "properties": {
                    "objectid": row.objectid,
                    "permit_no": row.permit_no,
                    "mobility_impact_text": row.mobility_impact_text,
                    "permit_address_text": row.permit_address_text,
                    "applicant_name": row.applicant_name
                }
            }
            jsoned.append(result_dict)
        return jsoned


class SidewalkElevationsAPI(Resource):
    def get(self):
        args = parser.parse_args()
        if args['bbox']:
            bbox = [float(point) for point in args["bbox"].split(",")]
            results = bbox_filter(SidewalkElevation, bbox)
        else:
            results = SidewalkElevation.query.limit(N_RESULTS_DEFAULT)
            print N_RESULTS_DEFAULT
        jsoned = []
        for row in results:
            geom = wkt.loads(db.session.scalar(row.coordinates.wkt))
            result_dict = {
                "type": geom["type"],
                "coordinates": geom["coordinates"],
                "properties": {
                    "sidewalk_objectid": row.sidewalk_objectid,
                    "grade": row.grade
                }
            }
            jsoned.append(result_dict)
        return jsoned


def bbox_filter(table, bbox):
    """Table is actual table object, bbox is of the form
    [lon1, lat1, lon2, lat2]

    """
    # Generate the polygon for the bounding box
    coords = [[bbox[0], bbox[1]], [bbox[0], bbox[3]], [bbox[2], bbox[3]],
              [bbox[2], bbox[1]], [bbox[0], bbox[1]]]
    wkt_polygon = wkt.dumps({'type': 'Polygon', 'coordinates': [coords]},
                            decimals=6)
    print wkt_polygon

    # Query the database and return the result
    query = db.session.query(table)
    filtered = query.filter(table.coordinates.intersects(wkt_polygon))
    resolved = [x for x in filtered]
    print len(resolved)

    return resolved


@app.route("/")
def index():
    return "Hackcessible API site - access is secret!"


api.add_resource(CurbsAPI, "/curbs.json")
api.add_resource(PermitsAPI, "/permits.json")
api.add_resource(SidewalkElevationsAPI, "/sidewalks.json")
