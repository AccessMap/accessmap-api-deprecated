from . import db
import geojson
import json
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import griddata


def get_isochrone(lonlat, costcol='cost'):
    '''Calculates ST_drivingDistance using the routing cost function for use in
    displaying isochrones.

    :param lonlat: Lon-lat (geoJSON) coordinates of isochrone center.
    :type lonlat: list
    :param costcol: column in isochronerouting table to use as cost
    :type costcol: str

    '''
    # Find node closest to isochrone center

    lon = float(lonlat[0])
    lat = float(lonlat[1])
    point = 'ST_Setsrid(ST_Makepoint({}, {}), 4326)'.format(lon, lat)

    closest_node_sql = '''
      SELECT id
        FROM isochroneroutingnodes
    ORDER BY ST_Distance(geom, ST_Transform({}, 2926))
       LIMIT 1;
    '''.format(point)

    result = db.engine.execute(closest_node_sql)
    start_node = list(result)[0][0]
    result.close()

    isochrone_sql = """
    SELECT cost,
           ST_AsGeoJSON(ST_Transform(geom, 4326)) AS geom
      FROM pgr_drivingDistance(
           'SELECT id,
                   source::int4,
                   target::int4,
                   {} AS cost
              FROM isochronerouting',
           {},
           10000,
           false,
           false) AS di
      JOIN isochroneroutingnodes AS pt
        ON di.id1 = pt.id;
    """

    isochrone_sql = isochrone_sql.format(costcol, start_node)
    result = db.engine.execute(isochrone_sql)
    isochrone_nodes = list(result)
    result.close()

    # Process into contour polygons
    x = []
    y = []
    z = []
    for node in isochrone_nodes:
        print(node)
        geometry = json.loads(node[1])
        x_, y_ = geometry['coordinates']
        z_ = node[0]
        x.append(x_)
        y.append(y_)
        z.append(z_)
    x = np.array(x)
    y = np.array(y)
    z = np.array(z)

    numcols, numrows = 150, 150
    xi = np.linspace(x.min(), x.max(), numcols)
    yi = np.linspace(y.min(), y.max(), numrows)
    xi, yi = np.meshgrid(xi, yi)
    # zi = griddata((x, y), z, (xi, yi), 'nearest')
    zi = griddata((x, y), z, (xi, yi))

    im = plt.contourf(xi, yi, zi)

    fc = geojson.FeatureCollection([])

    for i, collection in enumerate(im.collections):
        for path in collection.get_paths():
            polygons = [polygon.tolist() for polygon in path.to_polygons()]
            feature = geojson.Feature()
            feature['properties'] = {'level': i,
                                     'cost_max': im.levels[i + 1],
                                     'cost_min': im.levels[i]}
            feature['geometry'] = {'type': 'Polygon',
                                   'coordinates': polygons}
            fc['features'].append(feature)

    return fc
