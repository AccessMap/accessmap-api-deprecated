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
    d = 0
    for i, coord in enumerate(coords):
        if i == 0:
            pass
        last_coord = coords[i - 1]

        x1, y1 = last_coord
        x2, y2 = coord

        radius = 6371  # km
        dx = math.radians(x2 - x1)
        dy = math.radians(y2 - y1)

        a = math.sin(dy / 2) * math.sin(dy / 2) + \
            math.cos(math.radians(y1)) * math.cos(math.radians(y2)) * \
            math.sin(dx / 2) * math.sin(dx / 2)

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        d_km = radius * c
        d += d_km * 1000.

    return d
