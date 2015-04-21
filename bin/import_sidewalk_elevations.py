import json
from app import db, SidewalkElevation


# Expect a list of geojsons in the file
def import_sidewalk_elevations(geojson_path):
    with open(geojson_path) as f:
        geojson = json.load(f)

    sidewalk_elevations = []
    sidewalks_list = geojson["features"]
    for sidewalk_segment in sidewalks_list:
        sidewalk_elevation = SidewalkElevation(sidewalk_segment)
        sidewalk_elevations.append(sidewalk_elevation)

    db.session.add_all(sidewalk_elevations)
    db.session.commit()


if __name__ == "__main__":
    """Usage: python import_sidewalk_elevations.py path/to/sidewalk_elevations.json"""
    import sys
    arg1 = sys.argv[1]

    import_sidewalk_elevations(arg1)
