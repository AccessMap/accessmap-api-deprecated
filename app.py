from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from flask_restful import Api, Resource

# from geoalchemy2 import Geometry
# from geoalchemy2.shape import to_shape

# import os
# os.environ["GEOS_LIBRARY_PATH"] = "/homes/gws/bolten/local_install/lib/libgeos_c.so"
# print os.environ

from geomet import wkt


app = Flask(__name__, instance_relative_config=True)
# FIXME: put user and pass in a config for production
# Get default config (main app dir config.py)
app.config.from_object('config')
# Get instance config (hidden from git, is in app dir/instance/config.py)
app.config.from_pyfile('config.py')

db = SQLAlchemy(app)
migrate = Migrate(app, db)
api = Api(app)

manager = Manager(app)
manager.add_command('db', MigrateCommand)


# Database models
class Curb(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sidewalk_objectid = db.Column(db.Integer)
    geom = db.Column(db.String(16))
    # It's a 2-tuple of coordinates, not sure how to store this without
    # making another table. For now, just storing JSON directly.
    # If this were just like geoJSON, this would be in a properties table
    angle = db.Column(db.Float)

    def __init__(self, sidewalk_objectid, point, angle):
        self.sidewalk_objectid = sidewalk_objectid
	self.geom = wkt.dumps(point)
        self.angle = angle


class SidewalkElevation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sidewalk_objectid = db.Column(db.Integer)
    geom = db.Column(db.String(16))
    grade = db.Column(db.Float)

    def __init__(self, sidewalk_objectid, linestring, grade):
        self.sidewalk_objectid = sidewalk_objectid
        self.geom = wkt.dumps(linestring)
        self.grade = grade


class SidewalkElevationsAPI(Resource):
    def get(self):
        results = SidewalkElevation.query.all()
        jsoned = []
        for row in results:
            result_dict = {
                'type': 'LineString',
                'coordinates': list(wkt.loads(row.geom)["coordinates"]),
                'properties': {
                    'sidewalk_objectid': row.sidewalk_objectid,
                    'grade': row.grade
                }
            }
            jsoned.append(result_dict)
        return jsoned


class CurbsAPI(Resource):
    def get(self):
        results = Curb.query.all()
        jsoned = []
        for row in results:
            result_dict = {
                'type': 'Point',
                'coordinates': list(wkt.loads(row.geom)["coordinates"]),
                'properties': {
                    'sidewalk_objectid': row.sidewalk_objectid,
                    'angle': row.angle
                }
            }
            jsoned.append(result_dict)
        return jsoned


api.add_resource(SidewalkElevationsAPI, '/sidewalks.json')
api.add_resource(CurbsAPI, '/curbs.json')


@app.route("/")
def index():
    return "Hackcessible API site - access is secret!"


if __name__ == '__main__':
    manager.run()
