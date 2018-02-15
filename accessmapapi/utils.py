import geopandas as gpd
import math
import pyproj
from shapely.geometry import LineString, Point
from shapely import ops


RADIUS = 6378100  # Radius of the earth in meters


def cut(line, distance):
    # Cuts a line in two at a distance from its starting point
    if distance <= 0.0 or distance >= line.length:
        return [LineString(line)]
    coords = list(line.coords)
    for i, p in enumerate(coords):
        pd = line.project(Point(p))
        if pd == distance:
            return [
                LineString(coords[:i+1]),
                LineString(coords[i:])]
        if pd > distance:
            cp = line.interpolate(distance)
            return [
                LineString(coords[:i] + [(cp.x, cp.y)]),
                LineString([(cp.x, cp.y)] + coords[i:])]


def haversine(coords):
    # Given a list of coordinates (e.g. linestring.coords), calculate the
    # great circle length of the line, in meters

    d_tot = 0
    for i, coord in enumerate(coords):
        if i == 0:
            continue
        last_coord = coords[i - 1]

        lon1, lat1 = last_coord
        lon2, lat2 = coord

        dlon = math.radians(lon2 - lon1)
        dlat = math.radians(lat2 - lat1)

        a = math.sin(dlat / 2)**2 + \
            math.cos(math.radians(lat2)) * math.cos(math.radians(lat1)) * \
            math.sin(dlon / 2)**2

        d = 2 * RADIUS * math.asin(math.sqrt(a))
        d_tot += d

    return d_tot


def bbox_from_center(lon, lat, meters):
    # Create a bounding box array ([w,s,e,n]) given a center lon-lat and
    # distance (it creates a square, more or less).
    a = meters / (2 * RADIUS)
    b = math.sin(a)**2

    # We're separately finding lat and lon distances - in each case, we assume
    # that dlat = 0 or dlon = 0 to make easier calcs.

    # If dlon = 0, then math.sin(dlon) = 0 and only the first term matters.
    lat2 = math.asin(math.sqrt(b))
    dlat = math.degrees(abs(lat2 - lat))

    # If dlat = 0, first term is 0 and lat1 = lat2 = lat
    dlon = 2 * math.asin(math.sqrt(b / math.cos(math.radians(lat))**2))
    dlon = math.degrees(dlon)

    bbox = [lon - dlon,  lat - dlat, lon + dlon, lat + dlat]

    return bbox


def sindex_lonlat_nearest(lon, lat, meters, sindex, G):
    # Logic:
    # 1) Make a 'maximum search distance' bounding box
    # 2) Get all the features in it
    # 3) Filter (eventually)
    # 4) Get the closest valid path

    # Get the bounding box
    bbox = bbox_from_center(lon, lat, meters)

    # Query for features, extract
    query = sindex.intersection(bbox, objects=True)
    features = []
    for q in query:
        if q.object['type'] == 'edge':
            # It's an edge!
            features.append(G[q.object['lookup'][0]][q.object['lookup'][1]])
        else:
            # It's a node - ignore it! We'll look it up later if we found an
            # endpoint.
            pass

    features = gpd.GeoDataFrame(features)
    features.crs = {'init': 'epsg:4326'}

    # TODO: insert filtering logic here - e.g. can't cross the street.

    # Project to UTM (based on centerpoint) for pretty good nearest neighbor
    # calculation
    utm_zone_epsg = 32700 - 100 * round((45 + lat) / 90.) + \
        round((183 + lon) / 6.)

    features_utm = features.to_crs({'init': 'epsg:{}'.format(utm_zone_epsg)})
    wgs84 = pyproj.Proj(init='epsg:4326')
    utm = pyproj.Proj(init='epsg:{}'.format(utm_zone_epsg))
    center_utm = Point(pyproj.transform(wgs84, utm, lon, lat))

    features_utm['distance'] = features_utm.distance(center_utm)

    feature = features_utm.sort_values('distance').iloc[0]
    geom_utm = feature.geometry

    # Closest point on that feature
    distance_along = geom_utm.project(center_utm)

    def proj(x, y):
        return pyproj.transform(utm, wgs84, x, y)

    # Decide whether to return the edge of point
    if distance_along < 0.1:
        # We should use the 'start' node
        return {
            'type': 'node',
            'lookup': feature['from']
        }
    elif (geom_utm.length - distance_along) < 0.1:
        # We should use the 'end' node
        return {
            'type': 'node',
            'lookup': feature['to']
        }
    else:
        # We should use the edge.
        fraction_along = geom_utm.project(center_utm, normalized=True)
        distance = geom_utm.length * fraction_along
        geom_u, geom_v = cut(geom_utm, distance)
        length_u = geom_u.length
        length_v = geom_v.length
        geom_u_wgs84 = ops.transform(proj, geom_u)
        geom_v_wgs84 = ops.transform(proj, geom_v)

        return {
            'type': 'edge',
            'lookup': [feature['from'], feature['to']],
            'geometry_u': geom_u_wgs84,
            'length_u': length_u,
            'geometry_v': geom_v_wgs84,
            'length_v': length_v,
        }
