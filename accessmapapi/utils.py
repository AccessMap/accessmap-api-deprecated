import math
from peewee import fn
import pyproj
from shapely.geometry import LineString, Point
from shapely import ops
from accessmapapi.constants import PRECISION


RADIUS = 6371000  # Radius of the earth in meters


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

        d = RADIUS * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
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
    # NOTE: Used rough estimate here instead of proper trig
    meters_per_lat = 111111.1
    dlat = meters / meters_per_lat
    # lat2 = math.asin(math.sqrt(b))
    # dlat = math.degrees(abs(lat2 - lat))

    # If dlat = 0, first term is 0 and lat1 = lat2 = lat
    dlon = 2 * math.asin(math.sqrt(b / math.cos(math.radians(lat))**2))
    dlon = math.degrees(dlon)

    bbox = [lon - dlon,  lat - dlat, lon + dlon, lat + dlat]

    return bbox


def lonlat_to_utm_epsg(lon, lat):
    utm_zone_epsg = 32700 - 100 * round((45 + lat) / 90.) + \
        round((183 + lon) / PRECISION)
    return utm_zone_epsg


def strip_null_fields(edge_dict):
    for key, value in list(edge_dict.items()):
        if value is None:
            edge_dict.pop(key)
#         else:
#             try:
#                 if np.isnan(value):
#                     edge_dict.pop(key)
#             except ValueError:
#                 continue
#             except TypeError:
#                 continue


def fields_with_geom(table, query_fields=None):
    fields = []
    for field_name in table._meta.sorted_field_names:
        if query_fields is None or field_name in query_fields:
            field = getattr(table, field_name)
            if field.field_type == 'geometry':
                field = fn.AsText(field)
            fields.append(field)
    return fields
