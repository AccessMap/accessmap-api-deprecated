from accessmapapi import app
from accessmapapi.routing import costs, route, travelcost
from flask import g, jsonify, request
import geojson
from shapely.geometry import mapping, Point


@app.route('/v2/sidewalks.geojson')
def sidewalksv2():
    # TODO: return proper codes and messages when bad inputs are given
    bbox = request.args.get('bbox')
    all_rows = request.args.get('all')

    gdf = g['sidewalks']

    if all_rows == 'true':
        fc = gdf_to_fc(gdf)
    else:
        if not bbox:
            fc = gdf_to_fc(gdf.iloc[:10])
        else:
            bounds = [float(b) for b in bbox.split(',')]
            query = gdf.sindex.intersects(bounds, objects=True)
            in_bounds = gdf.loc[[q.index for q in query]]
            fc = gdf_to_fc(in_bounds)

    return jsonify(fc)


@app.route('/v2/crossings.geojson')
def crossingsv2():
    # TODO: return proper codes and messages when bad inputs are given
    bbox = request.args.get('bbox')
    all_rows = request.args.get('all')

    gdf = g['crossings']

    if all_rows == 'true':
        fc = gdf_to_fc(gdf)
    else:
        if not bbox:
            fc = gdf_to_fc(gdf.iloc[:10])
        else:
            bounds = [float(b) for b in bbox.split(',')]
            query = gdf.sindex.intersects(bounds, objects=True)
            in_bounds = gdf.loc[[q.index for q in query]]
            fc = gdf_to_fc(in_bounds)

    return jsonify(fc)


@app.route('/v2/elevator_paths.geojson')
def elevator_pathsv2():
    # TODO: return proper codes and messages when bad inputs are given
    bbox = request.args.get('bbox')
    all_rows = request.args.get('all')

    gdf = g['elevator_paths']

    if all_rows == 'true':
        fc = gdf_to_fc(gdf)
    else:
        if not bbox:
            fc = gdf_to_fc(gdf.iloc[:10])
        else:
            bounds = [float(b) for b in bbox.split(',')]
            query = gdf.sindex.intersects(bounds, objects=True)
            in_bounds = gdf.loc[[q.index for q in query]]
            fc = gdf_to_fc(in_bounds)

    return jsonify(fc)


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
    params = ['avoid', 'incline_min', 'incline_max']
    cost_params = {
        'avoid_curbs': False
    }

    # Params
    for param in params:
        value = request.args.get(param, None)
        if value is not None:
            if param == 'avoid':
                # Process barriers - pipe-separated e.g. curbs|construction
                barriers = value.split('|')
                if 'curbs' in barriers:
                    cost_params['avoid_curbs'] = True
            elif param == 'incline_max':
                cost_params['incline_max'] = float(value)
            elif param == 'incline_min':
                cost_params['incline_min'] = float(value)
            elif param == 'base_speed':
                cost_params['base_speed'] = float(value)

    origin_coords = [float(c) for c in origin.split(',')]
    destination_coords = [float(c) for c in destination.split(',')]

    origin = Point(reversed(origin_coords))
    destination = Point(reversed(destination_coords))

    route_response = route.dijkstra(origin, destination,
                                    cost_fun_gen=costs.cost_fun_generator,
                                    cost_kwargs=cost_params)

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
