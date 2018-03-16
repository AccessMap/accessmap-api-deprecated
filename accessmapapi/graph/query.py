'''Queries on the routing graph - generall geospatial.'''
import geopandas as gpd
from shapely.geometry import LineString, Point
from accessmapapi.utils import bbox_from_center, lonlat_to_utm_epsg


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
    utm_code = lonlat_to_utm_epsg(lon, lat)

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

    gdf = gpd.GeoDataFrame(rows)
    gdf.crs = {'init': 'epsg:4326'}
    gdf_utm = gdf.to_crs({'init': 'epsg:{}'.format(utm_code)})

    point = Point([lon, lat])
    points = gpd.GeoSeries([point])
    points.crs = {'init': 'epsg:4326'}
    points_utm = points.to_crs({'init': 'epsg:{}'.format(utm_code)})
    point_utm = points_utm.iloc[0]

    gdf_utm['distance'] = gdf_utm.distance(point_utm)

    gdf_utm = gdf_utm[gdf_utm['distance'] < distance]

    gdf_utm = gdf_utm.sort_values('distance')

    return gdf_utm


def closest_nonintersecting_edge(G, sindex, lon, lat, distance, filter=None):
    point = Point([lon, lat])
    utm_code = lonlat_to_utm_epsg(lon, lat)
    points = gpd.GeoSeries([point])
    points.crs = {'init': 'epsg:4326'}
    points_utm = points.to_crs({'init': 'epsg:{}'.format(utm_code)})
    point_utm = points_utm.iloc[0]

    gdf_sorted = dwithin(G, sindex, lon, lat, distance)

    for idx, row in gdf_sorted.iterrows():
        if row['type'] == 'edge':
            u, v = row['lookup']
            edge = G[u][v]
            if filter is not None:
                if not filter(edge):
                    continue

            geom = row.geometry
            point2 = geom.interpolate(geom.project(point_utm))
            line = LineString([point_utm, point2])
            if gdf_sorted[gdf_sorted.index != idx].intersects(line).any():
                continue

            return edge

    return None
