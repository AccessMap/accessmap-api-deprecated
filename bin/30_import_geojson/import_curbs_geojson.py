import geojson
from app import db
from app.models import Curb


# Expect a geojson FeatureCollection
def import_curbs(geojson_path):
    with open(geojson_path) as f:
        geojson_fc = geojson.load(f)

    for feature in geojson_fc['features']:
        curb = Curb(feature)
        db.session.add(curb)

    db.session.commit()


if __name__ == '__main__':
    '''Usage: python import_curbs.py path/to/curbs.json'''
    import sys
    arg1 = sys.argv[1]

    import_curbs(arg1)
