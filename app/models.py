from app import db
from geoalchemy import GeometryColumn, LineString, Point
from geomet import wkt


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
        self.coordinates = wkt.dumps(geojson)
        self.angle = geojson["properties"]["angle"]


class Permit(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    coordinates = GeometryColumn(Point(2))
    objectid = db.Column(db.Integer)
    permit_no = db.Column(db.Integer)
    mobility_impact_text = db.Column(db.String(2048))
    permit_address_text = db.Column(db.String(2048))
    applicant_name = db.Column(db.String(1024))

    def __init__(self, feature):
        # feature is a geoJSON feature
        self.coordinates = wkt.dumps(feature["geometry"])
        properties = feature["properties"]

        self.objectid = properties["objectid"]
        self.permit_no = properties["permit_no"]
        self.mobility_impact_text = properties["mobility_impact_text"]
        self.permit_address_text = properties["permit_address_text"]
        self.applicant_name = properties["applicant_name"]


class SidewalkElevation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sidewalk_objectid = db.Column(db.Integer)
    coordinates = GeometryColumn(LineString(2))
    grade = db.Column(db.Float)

    def __init__(self, geojson):
        self.sidewalk_objectid = geojson["properties"]["sidewalk_objectid"]
        self.coordinates = wkt.dumps(geojson["geometry"])
        self.grade = geojson["properties"]["grade"]
