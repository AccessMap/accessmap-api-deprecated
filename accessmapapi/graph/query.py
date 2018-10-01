'''Queries on the routing graph - generall geospatial.'''
import copy
import math
import pyproj
from shapely.geometry import LineString, Point
from shapely import wkt
from accessmapapi.utils import bbox_from_center, cut, lonlat_to_utm_epsg
from accessmapapi.utils import strip_null_fields, fields_with_geom


def closest_valid_startpoints(table, lon, lat, distance, cost_fun,
                              dest=False):
    utm_zone = lonlat_to_utm_epsg(lon, lat)
    wgs84 = pyproj.Proj(init='epsg:4326')
    utm = pyproj.Proj(init='epsg:{}'.format(utm_zone))
    point_utm = Point(pyproj.transform(wgs84, utm, lon, lat))

    db = table._meta.database

    bbox = bbox_from_center(lon, lat, distance)
    within_bbox_sql = '''
    SELECT rowid
      FROM SpatialIndex
     WHERE f_table_name = 'edges'
       AND search_frame = BuildMbr(?, ?, ?, ?, 4326)
    '''
    rows_within_bbox = db.execute_sql(within_bbox_sql, bbox).fetchall()
    # We need to extract the geometry as WKT, and get all the rows - iterate over the
    # columns
    fields = fields_with_geom(table, table._meta.sorted_field_names)
    # Note: could add reprojection in the select statement, probably faster
    edges_within_bbox = table.select(*fields).where(table.id << rows_within_bbox).dicts()

    # For some reason the output column is named 'geometry")'. Not sure why.
    for edge in edges_within_bbox:
        edge['geometry'] = wkt.loads(edge['geometry")'])
        utm_coords = []
        for x, y in edge['geometry'].coords:
            utm_coords.append(pyproj.transform(wgs84, utm, x, y))
        utm_geom = LineString(utm_coords)
        edge['geometry_utm'] = utm_geom
        edge['distance'] = utm_geom.distance(point_utm)

    sorted_edges = sorted(edges_within_bbox, key=lambda x: x['distance'])

    # TODO: add field null check here - remove edge keys with null values (None or nan)
    for i, box_edge in enumerate(sorted_edges):
        strip_null_fields(box_edge)
        box_edge.pop('distance')
        box_edge.pop('geometry")')

        # Check for intersections between query point and other intermediate edges
        distance_along = box_edge['geometry_utm'].project(point_utm)
        point2 = box_edge['geometry_utm'].interpolate(distance_along)
        line = LineString([point_utm, point2])
        for j, e in enumerate(sorted_edges):
            if i != j:
                if box_edge['geometry_utm'].intersects(line):
                    continue

        if distance_along < 0.1:
            # We're at an endpoint. Enumerate and evaluate edges
            u = box_edge['u']
            # Get adjacent edges
            adjacent = table.select().where(table.u == u).dicts()

            for edge in adjacent:
                v = edge['v']
                cost = cost_fun(u, v, edge)
                if cost != math.inf:
                    x, y = point2.coords[0]
                    p = Point(pyproj.transform(utm, wgs84, x, y))
                    return [{
                        'node': u,
                        'initial_cost': 0,
                        'point': p
                    }]
        elif (box_edge['geometry_utm'].length - distance_along) < 0.1:
            # We're at an endpoint. Enumerate and evaluate edges
            u = box_edge['v']
            # Get adjacent edges
            adjacent = table.select(*fields_with_geom(table)).where(table.u == u).dicts()

            for edge in adjacent:
                v = edge['v']
                cost = cost_fun(u, v, edge)
                if cost != math.inf:
                    x, y = point2.coords[0]
                    p = Point(pyproj.transform(utm, wgs84, x, y))
                    return [{
                        'node': u,
                        'initial_cost': 0,
                        'point': p
                    }]
        else:
            # We're along the edge. Split and evaluate 2 new edges.
            new_edges = cut(box_edge['geometry_utm'], distance_along)

            edge1 = copy.deepcopy(box_edge)
            edge1['v'] = -1
            edge1['geometry_utm'] = new_edges[0]

            edge2 = copy.deepcopy(box_edge)
            edge2['u'] = -1
            edge2['geometry_utm'] = new_edges[1]

            if dest:
                # Edges should point towards destination
                edge2 = reverse_edge(edge2)
            else:
                # Edges should point away from origin
                edge1 = reverse_edge(edge1)

            results = []
            for edge in [edge1, edge2]:
                edge['length'] = edge['geometry_utm'].length
                cost = cost_fun(edge['u'], edge['v'], edge)

                if cost is not None:
                    # Reproject to lon-lat and return results
                    x, y = point2.coords[0]
                    p = Point(pyproj.transform(utm, wgs84, x, y))
                    g2 = LineString([pyproj.transform(utm, wgs84, x, y)
                                     for x, y in edge['geometry_utm'].coords])
                    edge['geometry'] = g2
                    edge.pop('geometry_utm')
                    if 'geometry_utm' in box_edge:
                        box_edge.pop('geometry_utm')

                    # FIXME: are initial_edge and original_edge redundant?
                    # TODO: Decide whether all of these keys are necessary
                    results.append({
                        'node': edge['u'] if dest else edge['v'],
                        'initial_cost': cost,
                        'initial_edge': edge,
                        'original_edge': box_edge,
                        'point': p
                    })
            if results:
                return results

    return None


def reverse_edge(edge):
    new_edge = copy.deepcopy(edge)
    # FIXME: this should use the 'invert' properties defined in the layer config. This
    # should be something that exist either in the database or is passed around in
    # global flask config.
    new_edge['u'] = edge['v']
    new_edge['v'] = edge['u']
    if 'incline' in edge and edge['incline'] is not None:
        new_edge['incline'] = -1.0 * edge['incline']
    coords = reversed(edge['geometry_utm'].coords)
    new_edge['geometry_utm'].coords = list(coords)
    return new_edge
