import geojson
import json
import math


def geojsonify(raw_json):
    # This is the raw data from SDOT (not processed at all)

    # We want to extract this info in geoJSON format:
    # A list of curb object with these attributes:
    #   {'type': 'Point',
    #    'coordinates': coordinates,
    #    'properties': {
    #       'vector': vector indicating the direction of the curb
    #       'sidewalk_objectid': the objectid of the sidewalk for relationships
    #    }

    # FIXME: lon and lat are not equivalent distances - need to convert to
    # meters first *or* make a lat-lon vector instead.
    def angle(lon1, lat1, lon2, lat2):
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        return math.atan2(dlat, dlon)

    curb_list = []
    for sidewalk in raw_json:
        sidewalk_objectid = sidewalk['objectid']

        # Curbramp existence - high, mid, and low. They do not have their own
        # coordinates - their location can only be figured out using extra
        # information (not sure which key to use, at the moment)
        curbramp_high = sidewalk['curbramphighyn'] == 'Y'
        # curbramp_mid = sidewalk['curbrampmidyn'] == 'Y'
        curbramp_low = sidewalk['curbramplowyn'] == 'Y'

        # Because we can't identify which side of the street is 'high' or
        # 'low', we will play it safe and keep only those with both 'high' and
        # 'low' curb ramps.
        if not curbramp_high or not curbramp_low:
            continue

        # Geometry info
        shape_geom = sidewalk['shape']['geometry']

        # Some sidewalks lack a geometry - ignore them
        if 'paths' not in shape_geom:
            continue

        paths = shape_geom['paths']

        # There may be more than one disjoint path - we're going to look at
        # the first and last ones (TODO: figure out if this is valid with
        # SDOT - does high vs. low always align with e.g. the first and
        # last paths?

        # Generate paths in the same format - a set of coordinates, the
        # last of which is terminal (by the road - i.e. the curb
        # coordinate)
        startpath = paths[0][:2]
        endpath = paths[-1][-2:]

        curb1 = startpath[0]
        curb2 = endpath[-1]

        angle1 = angle(startpath[1][1], startpath[1][0], startpath[0][1],
                       startpath[0][0])
        angle2 = angle(endpath[-2][1], endpath[-2][0], endpath[-1][1],
                       endpath[-1][0])

        geom1 = geojson.Point(curb1)
        geom2 = geojson.Point(curb2)

        props1 = {'angle': angle1, 'sidewalk_objectid': sidewalk_objectid}
        props2 = {'angle': angle2, 'sidewalk_objectid': sidewalk_objectid}

        feature1 = geojson.Feature(geometry=geom1, properties=props1)
        feature2 = geojson.Feature(geometry=geom2, properties=props2)

        curb_list.append(feature1)
        curb_list.append(feature2)

    return geojson.FeatureCollection(curb_list)


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print 'Usage: python <scriptname.py> <input.json> <output.geojson>'

    inputfile = sys.argv[1]
    outputfile = sys.argv[2]

    with open(inputfile) as f:
        raw_data = json.load(f)

    geojsoned = geojsonify(raw_data)

    with open(outputfile, 'w') as g:
        geojson.dump(geojsoned, g)
