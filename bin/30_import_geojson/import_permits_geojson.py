import geojson
from app import db
from app.models import Permit


# Expect a FeatureCollection
def import_permits(geojson_path):
    with open(geojson_path) as f:
        geojson_fc = geojson.load(f)

    for feature in geojson_fc['features']:
        permit = Permit(feature)
        db.session.add(permit)

    db.session.commit()


if __name__ == '__main__':
    '''Usage: python import_permits.py <input.geojson>'''
    import sys
    arg1 = sys.argv[1]

    import_permits(arg1)
