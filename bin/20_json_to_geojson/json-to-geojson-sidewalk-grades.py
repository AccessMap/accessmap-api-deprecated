import geojson
import json
import math


def haversine(lon1, lat1, lon2, lat2):
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


def geojsonify(raw_json):
    sidewalk_list = []
    for sidewalk in raw_json:
        # Each sidewalk may have more than one path (disjoint)
        paths_list = sidewalk['paths']
        elevations_list = sidewalk['elevations']
        sidewalk_objectid = sidewalk['sidewalk_objectid']

        for paths, elevations in zip(paths_list, elevations_list):
            for i in range(0, len(paths) - 1):
                # Iterate through each segment (paths and elevations) to
                # generate:
                #   The length of the segment
                #   The elevation change
                #   The slope

                # current segment coordinates
                lat1, lon1 = paths[i]
                lat2, lon2 = paths[i + 1]
                segment_coords = [[lon1, lat1], [lon2, lat2]]

                # Each elevation
                elevation1 = elevations[i]
                elevation2 = elevations[i + 1]

                # Calculate distance using the Haversine formula
                distance = haversine(lon1, lat1, lon2, lat2)

                # Incline is rise over run
                grade = abs(elevation2 - elevation1) / distance

                # Generate the geoJSON. Note that we have lost some
                # information - namely, exactly which segment of the sidewalk
                # with the given id it is. This information could be easily
                # restored in the future given a need + spec
                geom = geojson.LineString(segment_coords)
                props = {'grade': grade,
                         'sidewalk_objectid': sidewalk_objectid}
                feature = geojson.Feature(geometry=geom, properties=props)

                sidewalk_list.append(feature)

    return geojson.FeatureCollection(sidewalk_list)


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print 'Usage: python <scriptname.py> <input.json> <output.geojson>'

    inputfile = sys.argv[1]
    outputfile = sys.argv[2]

    with open(inputfile) as f:
        raw_json = json.load(f)

    geojsoned = geojsonify(raw_json)

    with open(outputfile, 'w') as g:
        geojson.dump(geojsoned, g)
