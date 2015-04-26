import time
import datetime
import json
import requests
from polyline.codec import PolylineCodec

ELEVATION_KEY = "AIzaSyBmks7o9iSjRrcrzrpRcFQl5fqv9xVxHg8"
ELEVATION_KEY = "AIzaSyDmjcUk7KbKVEo79W2-vYnYgOYKQ7C8Gm8"
ELEVATION_URL = "https://maps.googleapis.com/maps/api/elevation/json"

with open("./sidewalk-paths-latest.json") as f:
    paths_list = json.load(f)


# FIXME: change to all data after testign
# paths_list = paths_list[0:60]

# Extract the flat coordinates, make an associated list of IDs for deflattening
coordinates_list = []
ids = []
for paths in paths_list:
    for path in paths["paths"]:
        for coordinates in path:
            coordinates_list.append(coordinates)
            ids.append(paths["sidewalk_objectid"])


# Need to send the requests in batches to not exceed URl limits
def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]

# Split into chunks of ~25 so as not to exceed URL size (not actually checked
# prior to request
coordinates_chunks = [x for x in chunks(coordinates_list, 100)]

encoded_polylines = []
for chunk in coordinates_chunks:
    encoded_polylines.append(PolylineCodec().encode(chunk))

elevations = []
print "Number of requests to make: {}".format(len(encoded_polylines))
time.sleep(1)
for i, line in enumerate(encoded_polylines):
    successful = False
    while not successful:
        # Keep trying (in case you get 502)
        before = time.time()
        print "Trying request {}...".format(i + 1)
        # Request the elevations
        params = {"locations": u"enc:" + line,
                  "key": ELEVATION_KEY}
        r = requests.get(ELEVATION_URL, params=params)
        print r.status_code
        # If you miss some data, ignore it and keep going. Figure out what's
        # missing later
        if r.status_code == 200:
            successful = True
            for result in r.json()["results"]:
                elevations.append(result["elevation"])
        else:
            print "Failed request {}, retrying...".format(i + 1)
        after = time.time()
        if after - before < 0.2:
            time.sleep(after - before + 0.2)


# Create a nice list of dictionaries (json-ie) to use in visualization step
output = []

# Deflatten the output - go through the paths, consuming elevations
elevation_generator = (elevation for elevation in elevations)
for paths in paths_list:
    objectid = paths["sidewalk_objectid"]
    elevations_list = []
    for path in paths["paths"]:
        elevations = []
        for coordinates in path:
            elevations.append(elevation_generator.next())
        elevations_list.append(elevations)
    output.append({"paths": paths["paths"], "elevations": elevations_list,
                   "sidewalk_objectid": objectid})


today = datetime.date.today().isoformat()
with open("./sidewalk-elevation-{}.json".format(today), "w") as f:
    json.dump(output, f)

with open("./sidewalk-elevation-latest.json", "w") as f:
    json.dump(output, f)
