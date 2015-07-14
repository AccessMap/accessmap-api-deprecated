import geojson
import json


def geojsonify(raw_json):
    # Generate a featurecollection geoJSON - the features are the permits
    feature_list = []
    for permit in raw_json:
        # Extract the location
        lat = float(permit['shape']['latitude'])
        lon = float(permit['shape']['longitude'])
        geom = geojson.Point([lon, lat])

        # Extract the properties we're interested in
        mobility_impact = ''
        if 'mobility_impact_text' in permit:
            mobility_impact = permit['mobility_impact_text']

        props = {'objectid': int(permit['objectid']),
                 'permit_no': int(permit['permit_no']),
                 'applicant_name': permit['applicant_name'],
                 'permit_address_text': permit['permit_address_text'],
                 'mobility_impact_text': mobility_impact}

        # Generate the feature geoJSON and add it to the features list
        feature = geojson.Feature(geometry=geom, properties=props)

        feature_list.append(feature)

    return geojson.FeatureCollection(feature_list)


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
