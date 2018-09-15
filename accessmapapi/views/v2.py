from accessmapapi.app import app
from accessmapapi.routing import costs, route, travelcost, walkshed
from flask import g, jsonify, request
import geojson
from shapely.geometry import mapping, Point

# FIXME: return proper error codes with messages for all methods (walkshed, etc)


@app.route('/v2/route.json', methods=['GET'])
def routev2():
    # Test coordinates:
    #   origin: 47.655883 -122.311994
    #   destination: 47.659877,-122.316052
    origin = request.args.get('origin', None)
    destination = request.args.get('destination', None)
    if (origin is None) or (destination is None):
        # TODO: return status code 400
        return jsonify({
            'status': 'BadInput',
            'errmessage': 'origin and destination parameters are required.'
        })

    # request route
    cost_params = process_cost_args(request.args)
    origin_coords = [float(c) for c in origin.split(',')]
    destination_coords = [float(c) for c in destination.split(',')]

    origin = Point(reversed(origin_coords))
    destination = Point(reversed(destination_coords))

    if g.costs is not None:
        cost_fun_gen = g.costs
    else:
        cost_fun_gen = costs.cost_fun_generator

    route_response = route.dijkstra(origin, destination,
                                    cost_fun_gen=cost_fun_gen,
                                    cost_kwargs=cost_params, layers=g.layers)

    return jsonify(route_response)


@app.route('/v2/travelcost.json', methods=['GET'])
def travelcostv2():
    # Process arguments
    # TODO: input validation - return reasonable HTTP errors on bad input.
    # latlon (required!)
    lat = request.args.get('lat', None)
    lon = request.args.get('lon', None)
    if lat is None or lon is None:
        return 'Bad request - lat and lon parameters are required.'

    # Calculate travel time
    costfun = costs.manual_wheelchair()
    cost_points = travelcost.travel_cost(lat, lon, costfun, maxcost=10000)

    return jsonify(cost_points)

@app.route('/v2/walkshed.json', methods=['GET'])
def walkshedv2():
    try:
        lon = float(request.args.get('lon', None))
        lat = float(request.args.get('lat', None))
        if lat is None or lon is None:
            return 'Bad request - lon and lat parameters are required.'
    except TypeError:
        return 'Bad request - lon and/or lat parameters are not numbers.'

    cutoff = request.args.get('cutoff', None)
    if cutoff is None:
        cutoff = 300  # Default to 300 seconds = 5 minutes
    else:
        try:
            cutoff = float(cutoff)
        except TypeError:
            return 'Bad request - cutoff must be a number.'

    # TODO: return bad request status if invalid avoid token is provided

    # Calculate the walkshed
    cost_params = process_cost_args(request.args)

    # TODO: swap out cost functions based on user preference, allow for 'cutoff' to
    # be separate metric from cost, e.g. total distance.
    if g.costs is not None:
        cost_fun_gen = g.costs
    else:
        cost_fun_gen = costs.cost_fun_generator


    the_walkshed = walkshed.walkshed(lon, lat, cost_fun_gen, cost_params, cutoff)

    return jsonify({
        'walkshed': the_walkshed
    })


def process_cost_args(request_args):
    '''Given a Flask request's arguments, process them into the keyword arguments
    expected by the cost function (stored as a dict).

    '''
    # request route
    params = ['avoid', 'incline_min', 'incline_max', 'speed', 'timestamp']
    cost_params = {
        'avoid_curbs': False
    }

    # Params
    for param in params:
        value = request_args.get(param, None)
        if value is not None:
            if param == 'avoid':
                # Process barriers - pipe-separated e.g. curbs|construction
                barriers = value.split('|')
                if 'curbs' in barriers:
                    cost_params['avoid_curbs'] = True
                if 'stairs' in barriers:
                    cost_params['avoid_stairs'] = True
            elif param == 'incline_max':
                cost_params['incline_max'] = float(value)
            elif param == 'incline_min':
                cost_params['incline_min'] = float(value)
            elif param == 'speed':
                cost_params['base_speed'] = float(value)
            elif param == 'timestamp':
                cost_params['timestamp'] = float(value) / 1000.0

    return cost_params


def gdf_to_fc(gdf):
    fc = geojson.FeatureCollection([])

    def row_to_feature(row):
        row = row.dropna()
        geometry = row.pop('geometry')
        feature = geojson.Feature()
        feature['geometry'] = mapping(geometry)
        feature['properties'] = dict(row)
        return feature

    fc['features'] = list(gdf.apply(row_to_feature, axis=1))

    return fc
