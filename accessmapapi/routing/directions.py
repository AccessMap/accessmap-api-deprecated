'''Module with functions for generating pedestrian directions information.'''
import copy


def path_to_directions(path, track=None):
    if track is None:
        track = []

    if 'way' not in track:
        track.append('way')

    # Iterate over each edge in the path
    steps = []
    for feature in path['features']:
        feature = copy.deepcopy(feature)
        properties = feature['properties']
        # If it's a `minor` properties, skip it. Being `minor` can either be a
        # category match (e.g., if we have a `link` property type we'd skip it)
        # or a check on numeric attributes (e.g. filter out very short steps).
        if 'length' in properties:
            if properties['length'] < 3:
                continue

        # If the properties we're tracking don't change, merge into one step.
        # e.g. a sidewalk may be split by a mid-block crossing, but so
        # long as we're continuing, no info will change.
        feature['properties'] = {}
        for k in track:
            if k in properties:
                feature['properties'][k] = properties[k]

        try:
            last = steps[-1]
        except IndexError:
            last = None

        if last is None:
            steps.append(feature)
        else:
            if last['properties']['way'] != properties['way']:
                changed = True
            else:
                changed = change(last['properties'], properties, track)

            if changed:
                steps.append(feature)
            else:
                if 'length' in last['properties'] and 'length' in properties:
                    last['properties']['length'] += properties['length']
                    add_coords = feature['geometry']['coordinates'][1:]
                    last['geometry']['coordinates'] += add_coords

    return steps


def change(prop1, prop2, track):
    if set(prop1.keys()) != set(prop2.keys()):
        return True
    for key in track:
        if prop1[key] != prop2[key]:
            return True
    return False
