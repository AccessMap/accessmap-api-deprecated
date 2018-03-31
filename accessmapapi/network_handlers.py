import geobuf
import geopandas as gpd
import os
import pickle
import rtree
from accessmapapi import network


def get_geobuf(app, layer_name):
    layer = app.config.get(layer_name, None)
    if layer is not None:
        return layer

    app.logger.info('Reading {} from data directory...'.format(layer_name))
    datadir = app.config['PEDDATADIR']

    with open(os.path.join(datadir, '{}.geobuf'.format(layer_name)), 'rb') as f:
        pbf = f.read()
        layer = geobuf.decode(pbf)

    df = gpd.GeoDataFrame.from_features(layer['features'])

    app.config[layer_name] = df

    return df


def get_G(app):
    # TODO: separate out spatial index from graph creation process to make
    # this simpler?
    G = app.config.get('G', None)

    if G is not None:
        return G

    app.logger.info('Graph or spatial index have not been loaded.')

    sidewalks = get_geobuf(app, 'sidewalks')
    crossings = get_geobuf(app, 'crossings')
    elevator_paths = get_geobuf(app, 'elevator_paths')

    datadir = app.config['PEDDATADIR']
    graph_path = os.path.join(datadir, 'graph.txt')

    # Logic:
    # 1. Attempt to read the spatial index.
    # 2. If reading the spatial index fails, recreate the graph and return.
    # 3. If the spatial index was successfully read, attempt to read the graph.
    # 4. If the graph can't be read, try to create it.

    def make_graph():
        # Create graph
        app.logger.info('Creating new graph. This may take a few minutes...')

        G = network.make_network(sidewalks, crossings, elevator_paths)

        # Serialize to file for posterity
        with open(os.path.join(datadir, 'graph.txt'), 'wb') as f:
            pickle.dump(G, f)

        app.config['G'] = G

        app.logger.info('Graph created.')

        return G

    # Attempt to read it in.
    if os.path.exists(graph_path):
        app.logger.info('Reading graph...')
        try:
            with open(graph_path, 'rb') as f:
                G = pickle.load(f)
                app.logger.info('Graph read.')

                app.config['G'] = G

                return G
        except:
            app.logger.info('Failed to read graph.')
    else:
        app.logger.info('No graph file found.')

    app.config['G'] = G
    G = make_graph()

    return G


def get_sindex(app):
    # Check if it's already in-memory
    sindex = app.config.get('sindex', None)

    if sindex is not None:
        return sindex

    # FIXME: libspatialindex can't do multithreading and the dev team doesn't
    # seem open to updating it. Consider rolling own rtree and/or just use
    # spatialite
    app.logger.info('Creating spatial index...')

    G = get_G(app)
    sindex = network.make_sindex(G)
    app.config['sindex'] = sindex

    app.logger.info('Spatial index created.')

    return sindex
