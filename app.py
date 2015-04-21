from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from flask_restful import Api, Resource, reqparse

from geoalchemy import GeometryColumn, LineString, Point

from geomet import wkt

app = Flask(__name__, instance_relative_config=True)
# FIXME: put user and pass in a config for production
# Get default config (main app dir config.py)
app.config.from_object("config")
# Get instance config (hidden from git, is in app dir/instance/config.py)
app.config.from_pyfile("config.py")

db = SQLAlchemy(app)
migrate = Migrate(app, db)
api = Api(app)

manager = Manager(app)
manager.add_command("db", MigrateCommand)

# Default query limit if no params are offered
N_RESULTS_DEFAULT = 100


# Database models
class Curb(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sidewalk_objectid = db.Column(db.Integer)
    coordinates = GeometryColumn(Point(2))
    # It"s a 2-tuple of coordinates, not sure how to store this without
    # making another table. For now, just storing JSON directly.
    # If this were just like geoJSON, this would be in a properties table
    angle = db.Column(db.Float)

    def __init__(self, geojson):
        self.sidewalk_objectid = geojson["properties"]["sidewalk_objectid"]
        self.coordinates = wkt.dumps(geojson, decimals=6)
        self.angle = geojson["properties"]["angle"]


class SidewalkElevation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sidewalk_objectid = db.Column(db.Integer)
    coordinates = GeometryColumn(LineString(2))
    grade = db.Column(db.Float)

    def __init__(self, geojson):
        self.sidewalk_objectid = geojson["properties"]["sidewalk_objectid"]
        self.coordinates = wkt.dumps(geojson["geometry"], decimals=4)
        self.grade = geojson["properties"]["grade"]


parser = reqparse.RequestParser()
# I think it's a string? [lon1,lat1,lon2,lat2]
parser.add_argument("bbox", type=str)


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


api.add_resource(SidewalkElevationsAPI, "/sidewalks.json")
api.add_resource(CurbsAPI, "/curbs.json")


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


if __name__ == "__main__":
    manager.run()
