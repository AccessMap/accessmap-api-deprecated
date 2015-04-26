import datetime
import json
import math


with open('./sidewalk-sdot-latest.json') as f:
    sidewalks = json.load(f)


# This is the raw data from SDOT (not processed at all)

# We want to extract this info in geoJSON format:
# A list of curb object with these attributes:
#   {'type': 'Point',
#    'coordinates': coordinates,
#    'properties': {
#       'vector': vector indicating the direction of the curb
#       'sidewalk_objectid': the objectid of the sidewalk for relationships
#    }

def find_angle(lon1, lat1, lon2, lat2):
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    return math.atan2(dlat, dlon)

sidewalk_geoJSONs = []
for sidewalk in sidewalks:
    # objectid of the sidewalk for relating to other data processed from this
    # dataset
    sidewalk_objectid = sidewalk['objectid']
    # Curbramp existence - high, mid, and low. They do not have their own
    # coordinates - their location can only be figured out using extra
    # information (not sure which key to use, at the moment)
    curbramp_high = sidewalk['curbramphighyn'] == 'Y'
    curbramp_mid = sidewalk['curbrampmidyn'] == 'Y'
    curbramp_low = sidewalk['curbramplowyn'] == 'Y'
    # At the moment - ignore if there aren't sidewalks at both ends until
    # we know how to choose which side is high vs low
    if curbramp_high and curbramp_low:
        # Geometry info
        shape = sidewalk['shape']
        geometry = shape['geometry']
        if 'paths' not in geometry:
            # For some reason, there's no paths in some of the geometries
            continue
        paths = shape['geometry']['paths']
        # There may be more than one disjoint path - we're going to look at
        # the first and last ones (TODO: figure out if this is valid with
        # SDOT - does high vs. low always align with e.g. the first and last
        # paths?
        # Generate paths in the same format - a set of coordinates, the last of
        # which is terminal (by the road - i.e. the curb coordinate)
        startpath = paths[0][:2]
        endpath = paths[-1][-2:]

        for path in (startpath, endpath):
            # (lon, lat) format
            curb_coord = path[-1]
            angle = find_angle(path[-1][0], path[-1][1], path[0][0],
                               path[0][1])
            geoJSON = {
                'type': 'Point',
                'coordinates': curb_coord,
                'properties': {
                    'angle': angle,
                    'sidewalk_objectid': sidewalk_objectid
                }
            }
            sidewalk_geoJSONs.append(geoJSON)


today = datetime.date.today().isoformat()
with open('./sdot-sidewalk-curb-geoJSON-{}.json'.format(today), 'w') as g:
    json.dump(sidewalk_geoJSONs, g)


with open('./sdot-sidewalk-curb-geoJSON-latest.json', 'w') as h:
    json.dump(sidewalk_geoJSONs, h)
