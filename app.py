from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from flask_restful import Api, Resource

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
    wkt = db.Column(db.String(1024))
    # It's a 2-tuple of coordinates, not sure how to store this without
    # making another table. For now, just storing JSON directly.
    # If this were just like geoJSON, this would be in a properties table
    angle = db.Column(db.Float)

    def __init__(self, geojson):
        self.sidewalk_objectid = geojson['properties']['sidewalk_objectid']
        self.wkt = wkt.dumps(geojson)
        self.angle = geojson['properties']['angle']


class SidewalkElevation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sidewalk_objectid = db.Column(db.Integer)
    wkt = db.Column(db.String(1024))
    grade = db.Column(db.Float)

    def __init__(self, geojson):
        self.sidewalk_objectid = geojson['properties']['sidewalk_objectid']
        self.wkt = wkt.dumps(geojson)
        self.grade = geojson['properties']['grade']


class SidewalkElevationsAPI(Resource):
    def get(self):
        results = SidewalkElevation.query.all()
        jsoned = []
        for row in results:
            result_dict = {
                'type': 'LineString',
                'coordinates': list(wkt.loads(row.wkt)["coordinates"]),
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
                'coordinates': list(wkt.loads(row.wkt)["coordinates"]),
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
