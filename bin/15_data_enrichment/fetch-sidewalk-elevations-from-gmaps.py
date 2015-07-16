import time
import json
import requests
from polyline.codec import PolylineCodec

ELEVATION_KEY = 'AIzaSyBmks7o9iSjRrcrzrpRcFQl5fqv9xVxHg8'
# ELEVATION_KEY = 'AIzaSyDmjcUk7KbKVEo79W2-vYnYgOYKQ7C8Gm8'
ELEVATION_URL = 'https://maps.googleapis.com/maps/api/elevation/json'


def make_elevation_segments(input_json):
    # FIXME: change to all data after testign
    input_json = input_json[0:60]

    # Extract the flat coordinates, make an associated list of IDs for
    # deflattening
    coordinates_list = []
    ids = []
    for sidewalk in input_json:
        for path in sidewalk['shape']['geometry']['paths']:
            for coordinates in path:
                coordinates_list.append(coordinates)
                ids.append(sidewalk['objectid'])

    # Need to send the requests in batches to not exceed URl limits
    def chunks(l, n):
        for i in range(0, len(l), n):
            yield l[i:i + n]

    # Split into chunks of ~25 so as not to exceed URL size (not actually
    # checked prior to request
    coordinates_chunks = [x for x in chunks(coordinates_list, 100)]

    encoded_polylines = []
    for chunk in coordinates_chunks:
        encoded_polylines.append(PolylineCodec().encode(chunk))

    elevations = []
    print 'Number of requests to make: {}'.format(len(encoded_polylines))
    time.sleep(1)
    for i, line in enumerate(encoded_polylines):
        successful = False
        while not successful:
            # Keep trying (in case it returns 502)
            before = time.time()
            print 'Trying request {}...'.format(i + 1)
            # Request the elevations
            params = {'locations': u'enc:' + line,
                      'key': ELEVATION_KEY}
            r = requests.get(ELEVATION_URL, params=params)
            print r.status_code
            # If you miss some data, ignore it and keep going. Figure out
            # what's missing later
            if r.status_code == 200:
                successful = True
                print r.json()
                for result in r.json()['results']:
                    elevations.append(result['elevation'])
            else:
                print 'Failed request {}, retrying...'.format(i + 1)
            after = time.time()
            if after - before < 0.2:
                time.sleep(after - before + 0.2)

    # Deflatten the output - go through the paths, consuming elevations
    print elevations
    elevation_generator = (elevation for elevation in elevations)
    output = []
    for sidewalk in input_json:
        objectid = sidewalk['objectid']
        elevations_list = []
        for path in sidewalk['shape']['geometry']['paths']:
            elevations = []
            for coordinates in path:
                elevations.append(elevation_generator.next())
            elevations_list.append(elevations)
        output.append({'paths': sidewalk['paths'],
                       'elevations': elevations_list,
                       'sidewalk_objectid': objectid})

    return output


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print 'Usage: python <scriptname.py> <input.json> <output.json>'

    inputfile = sys.argv[1]
    outputfile = sys.argv[2]

    with open(inputfile) as f:
        raw_data = json.load(f)

    elevation_segments = make_elevation_segments(raw_data)

    with open(outputfile, 'w') as g:
        json.dump(elevation_segments, g)
