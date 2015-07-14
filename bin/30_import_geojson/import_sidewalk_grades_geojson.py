import geojson
from app import db
from app.models import SidewalkGrade


# Expect a list of geojsons in the file
def import_sidewalk_grades(geojson_path):
    with open(geojson_path) as f:
        sidewalk_grades_fc = geojson.load(f)

    for feature in sidewalk_grades_fc['features']:
        sidewalk_grade = SidewalkGrade(feature)
        db.session.add(sidewalk_grade)

    db.session.commit()


if __name__ == '__main__':
    '''Usage: python import_sidewalk_grades.py <input.geojson>'''
    import sys
    arg1 = sys.argv[1]

    import_sidewalk_grades(arg1)
