'''Queries on the routing graph - generall geospatial.'''
import copy
import geopandas as gpd
import math
import pandas as pd
from peewee import fn
import pyproj
from shapely.geometry import LineString, Point
from shapely import wkt
from accessmapapi.utils import bbox_from_center, cut, lonlat_to_utm_epsg, geom_table_to_fields


def closest_valid_startpoints(table, lon, lat, distance, cost_fun,
                              dest=False):
    utm_zone = lonlat_to_utm_epsg(lon, lat)
    wgs84 = pyproj.Proj(init='epsg:4326')
    utm = pyproj.Proj(init='epsg:{}'.format(utm_zone))
    point_utm = Point(pyproj.transform(wgs84, utm, lon, lat))

    ##

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
    fields = geom_table_to_fields(table)
    edges_within_bbox = table.select(*fields).where(table.id << rows_within_bbox).dicts()

    # For some reason the output column is named 'geometry")'. Not sure why.
    df = pd.DataFrame(list(edges_within_bbox))
    df['geometry'] = df['geometry")'].apply(wkt.loads)
    df = df.drop(columns='geometry")')
    gdf = gpd.GeoDataFrame(df)
    gdf.crs = {'init': 'epsg:4326'}
    gdf_utm = gdf.to_crs({'init': 'epsg:{}'.format(utm_zone)})
    gdf_utm['distance'] = gdf_utm.distance(point_utm)
    gdf_sorted = gdf_utm.sort_values('distance')

    ##

    # TODO: add field null check here - remove edge keys with null values (None or nan)

    for idx, row in gdf_sorted.iterrows():
        row_edge = dict(row)
        row_edge.pop('distance')
        # Check for intersection
        distance_along = row.geometry.project(point_utm)
        point2 = row.geometry.interpolate(distance_along)
        line = LineString([point_utm, point2])
        non_idx = gdf[gdf_sorted.index != idx]
        if non_idx.intersects(line).any():
            continue

        if distance_along < 0.1:
            # We're at an endpoint. Enumerate and evaluate edges
            u = row_edge['u']
            # Get adjacent edges
            adjacent = table.select().where(table.u == u).dicts()

            for edge in adjacent:
                v = edge[v]
                cost = cost_fun(u, v, edge)
                if cost != math.inf:
                    x, y = point2.coords[0]
                    p = Point(pyproj.transform(utm, wgs84, x, y))
                    return [{
                        'node': u,
                        'initial_cost': 0,
                        'point': p
                    }]
        elif (row.geometry.length - distance_along) < 0.1:
            # We're at an endpoint. Enumerate and evaluate edges
            u = row_edge['v']
            # Get adjacent edges
            adjacent = table.select().where(table.u == u).dicts()

            for edge in adjacent:
                v = edge[u]
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
            new_edges = cut(row_edge['geometry'], distance_along)

            edge1 = copy.deepcopy(row_edge)
            edge1['v'] = -1
            edge1['geometry'] = new_edges[0]

            edge2 = copy.deepcopy(row_edge)
            edge2['u'] = -1
            edge2['geometry'] = new_edges[1]

            if dest:
                # Edges should point towards destination
                edge2 = reverse_edge(edge2)
            else:
                # Edges should point away from origin
                edge1 = reverse_edge(edge1)

            results = []
            for edge in [edge1, edge2]:
                edge['length'] = edge['geometry'].length
                cost = cost_fun(edge['u'], edge['v'], edge)

                if cost is not None:
                    # Reproject to lon-lat and return results
                    x, y = point2.coords[0]
                    p = Point(pyproj.transform(utm, wgs84, x, y))
                    g2 = LineString([pyproj.transform(utm, wgs84, x, y)
                                     for x, y in edge['geometry'].coords])
                    edge['geometry'] = g2

                    # FIXME: are initial_edge and original_edge redundant?
                    # TODO: Decide whether all of these keys are necessary
                    results.append({
                        'node': edge['u'] if dest else edge['v'],
                        'initial_cost': cost,
                        'initial_edge': edge,
                        'original_edge': row_edge,
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
    if 'incline' in edge:
        new_edge['incline'] = -1.0 * edge['incline']
    coords = reversed(edge['geometry'].coords)
    edge['geometry'].coords = list(coords)
    return new_edge
