import json
from app import db
from app.models import SidewalkGrade


# Expect a list of geojsons in the file
def import_sidewalk_grades(geojson_path):
    with open(geojson_path) as f:
        geojson = json.load(f)

    sidewalk_grades = []
    sidewalks_list = geojson["features"]
    for sidewalk_segment in sidewalks_list:
        sidewalk_grade = SidewalkGrade(sidewalk_segment)
        sidewalk_grades.append(sidewalk_grade)

    db.session.add_all(sidewalk_grades)
    db.session.commit()


if __name__ == "__main__":
    """Usage: python import_sidewalk_grades.py path/to/sidewalk_grades.json"""
    import sys
    arg1 = sys.argv[1]

    import_sidewalk_grades(arg1)
