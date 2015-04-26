import json
import math


def calculate_distance(lon1, lat1, lon2, lat2):
    '''Calculate the distance between two points given latitude and longitude
    coordinates. Uses the Haversine formula.'''
    # Radius of the earth in meters
    R = 6371 * 1000
    # Change in latitude and longitude
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2.)**2 + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon / 2.)**2
    c = 2. * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = R * c
    return d


with open('./sidewalk-elevation-latest.json') as f:
    raw_sidewalks = json.load(f)


# Generate a geoJSON for each one
geoJSON_sidewalks = []
for sidewalk in raw_sidewalks:
    # Each sidewalk may have more than one path (disjoint)
    paths_list = sidewalk['paths']
    elevations_list = sidewalk['elevations']
    sidewalk_objectid = sidewalk['sidewalk_objectid']

    for paths, elevations in zip(paths_list, elevations_list):
        # For every path (set of coordinates) and elevations (set of
        # elevations)
        for i in range(0, len(paths) - 1):
            # Iterate through each segment (paths and elevations) to generate:
            #   The length of the segment
            #   The elevation change
            #   The slope
            lat1, lon1 = paths[i]
            lat2, lon2 = paths[i + 1]
            # Longitude first for geoJSON standard
            segment_path = [[lon1, lat1], [lon2, lat2]]
            # Each elevation
            elevation1 = elevations[i]
            elevation2 = elevations[i + 1]
            # Calculate distance using the Haversine formula
            distance = calculate_distance(lon1, lat1, lon2, lat2)
            # Incline is rise over run
            grade = abs(elevation2 - elevation1) / distance

            # Generate the geoJSON. Note that we have lost some information -
            # namely, exactly which segment of the sidewalk with the given id
            # it is. This information could be easily restored in the future
            # given a need + spec
            geoJSON = {
                'type': 'LineString',
                'coordinates': segment_path,
                'properties': {
                    'grade': grade,
                    'sidewalk_objectid': sidewalk_objectid
                }
            }
            geoJSON_sidewalks.append(geoJSON)


with open('./sidewalk-grades-geoJSON-latest.json', 'w') as g:
    json.dump(geoJSON_sidewalks, g)
