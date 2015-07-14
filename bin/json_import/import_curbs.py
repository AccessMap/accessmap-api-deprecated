import json
from app import db
from app.models import Curb


# Expect a list of geojsons in the file
def import_curbs(geojson_path):
    with open(geojson_path) as f:
        geojson_list = json.load(f)

    curbs = []
    for geojson in geojson_list:
        curb = Curb(geojson)
        curbs.append(curb)

    db.session.add_all(curbs)
    db.session.commit()


if __name__ == "__main__":
    """Usage: python import_curbs.py path/to/curbs.json"""
    import sys
    arg1 = sys.argv[1]

    import_curbs(arg1)
