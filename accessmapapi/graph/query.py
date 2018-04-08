'''Queries on the routing graph - generall geospatial.'''
import copy
import geopandas as gpd
import math
import pyproj
from shapely.geometry import LineString, Point
from accessmapapi.utils import bbox_from_center, lonlat_to_utm_epsg, cut


def dwithin(G, sindex, lon, lat, distance):
    '''Returns a dictionary that contains a list (each) of nodes and edges from
    the graph that are within a specific distance of the lon-lat point.

    :param G: The routing graph.
    :type G: networkx.DiGraph
    :param sindex: The routing graph's spatial index.
    :type sindex: Rtree.Index
    :param lon: The longitude of the query point.
    :type lon: float
    :param lat: The latitude of the query point.
    :type lat: float
    :param distance: The query distance - circle radius, in meters.
    :type distance: float

    '''
    '''Overall strategy:
         1. Create a distance x distance bounding box
         2. Grab all graph elements that intersect this box (in the spatial
            index)
         3. Sort by haversine distance, disclude results that are outside of
            the distance range.
         4. Return { 'nodes': [id], 'edges': [id] } dict.

    '''
    bbox = bbox_from_center(lon, lat, distance)
    query = sindex.intersection(bbox, objects=True)

    rows = []
    for q in query:
        o = q.object

        if o['type'] == 'edge':
            u, v = o['lookup']
            o['geometry'] = G[u][v]['geometry']
        else:
            node = G.nodes[o['lookup']]
            o['geometry'] = Point([node['x'], node['y']])

        rows.append(o)

    utm_zone = lonlat_to_utm_epsg(lon, lat)
    wgs84 = pyproj.Proj(init='epsg:4326')
    utm = pyproj.Proj(init='epsg:{}'.format(utm_zone))

    gdf = gpd.GeoDataFrame(rows)
    gdf.crs = {'init': 'epsg:4326'}
    gdf_utm = gdf.to_crs({'init': 'epsg:{}'.format(utm_zone)})

    point_utm = Point(pyproj.transform(wgs84, utm, lon, lat))

    gdf_utm['distance'] = gdf_utm.distance(point_utm)
    gdf_utm = gdf_utm[gdf_utm['distance'] < distance]
    gdf_utm = gdf_utm.sort_values('distance')

    return gdf_utm


def closest_valid_startpoints(G, sindex, lon, lat, distance, cost_fun,
                              dest=False):
    utm_zone = lonlat_to_utm_epsg(lon, lat)
    wgs84 = pyproj.Proj(init='epsg:4326')
    utm = pyproj.Proj(init='epsg:{}'.format(utm_zone))
    point_utm = Point(pyproj.transform(wgs84, utm, lon, lat))

    gdf_sorted = dwithin(G, sindex, lon, lat, distance)

    for idx, row in gdf_sorted.iterrows():
        if row['type'] == 'edge':
            # Check for intersection
            distance_along = row.geometry.project(point_utm)
            point2 = row.geometry.interpolate(distance_along)
            line = LineString([point_utm, point2])
            if gdf_sorted[gdf_sorted.index != idx].intersects(line).any():
                continue

            # Check cost function against potential edge(s)
            # Note: this is done twice - pass result?
            ru, rv = row['lookup']
            row_edge = G[ru][rv]

            if distance_along < 0.1:
                # We're at an endpoint. Enumerate and evaluate edges
                u = row_edge['from']
                for v, edge in G[u].items():
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
                u = row_edge['to']
                for v, edge in G[u].items():
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
                u = -1
                new_edges = cut(row.geometry, distance_along)
                v1 = row_edge['from']
                v2 = row_edge['to']
                results = []
                for i, (geom, v) in enumerate(zip(new_edges, [v1, v2])):
                    edge = copy.deepcopy(row_edge)
                    if (dest and i == 1) or (not dest and i == 0):
                        # Initial route is in reverse direction from edge
                        coords = list(reversed(geom.coords))
                        geom.coords = coords
                        if 'incline' in edge:
                            edge['incline'] = -1.0 * edge['incline']

                    edge['geometry'] = geom

                    if dest:
                        cost = cost_fun(v, u, edge)
                    else:
                        cost = cost_fun(u, v, edge)
                    if cost != math.inf:
                        x, y = point2.coords[0]
                        p = Point(pyproj.transform(utm, wgs84, x, y))
                        g2 = LineString([pyproj.transform(utm, wgs84, x, y)
                                         for x, y in geom.coords])
                        edge['geometry'] = g2

                        results.append({
                            'node': v,
                            'initial_cost': cost,
                            'initial_edge': edge,
                            'original_edge': row_edge,
                            'point': p
                        })
                if results:
                    return results

    return None
