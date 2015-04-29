import json


with open('./permits-by-street-segment-latest.json') as f:
    raw_permits = json.load(f)


# Generate a featurecollection geoJSON - the features are the permits
geojson = {"type": "FeatureCollection",
           "features": []}

for permit in raw_permits:
    # Extract the location
    lat = float(permit["shape"]["latitude"])
    lon = float(permit["shape"]["longitude"])
    geometry = {"type": "Point",
                "coordinates": [lon, lat]}

    # Extract the properties we're interested in
    properties = {}
    properties["objectid"] = int(permit["objectid"])
    properties["permit_no"] = int(permit["permit_no"])
    properties["applicant_name"] = permit["applicant_name"]
    if "mobility_impact_text" in permit:
        properties["mobility_impact_text"] = permit["mobility_impact_text"]
    else:
        properties["mobility_impact_text"] = ""
    properties["permit_address_text"] = permit["permit_address_text"]

    # Generate the feature geoJSON and add it to the features list
    feature = {"type": "Feature",
               "geometry": geometry,
               "properties": properties}
    geojson["features"].append(feature)


with open('./permits-by-street-segment.geojson', 'w') as g:
    json.dump(geojson, g)
