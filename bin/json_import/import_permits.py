import json
from app import db
from app.models import Permit


# Expect a list of geojsons in the file
def import_permits(geojson_path):
    with open(geojson_path) as f:
        geojson_featurecollection = json.load(f)

    permits = []
    for feature in geojson_featurecollection["features"]:
        permit = Permit(feature)
        permits.append(permit)

    db.session.add_all(permits)
    db.session.commit()


if __name__ == "__main__":
    """Usage: python import_permits.py path/to/permits.geojson"""
    import sys
    arg1 = sys.argv[1]

    import_permits(arg1)
