import math
from shapely.geometry import LineString, Point


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
    RADIUS = 6378100  # Radius of the earth in meters

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
