import geobuf
import geopandas as gpd
import os
import pickle
import rtree  # noqa
from accessmapapi import network


def get_geobuf(path):
    with open(path, 'rb') as f:
        pbf = f.read()
        layer = geobuf.decode(pbf)
        df = gpd.GeoDataFrame.from_features(layer['features'])

    return df


def get_geobuf_cached(layer_name, app):
    layer = app.config.get(layer_name, None)
    if layer is not None:
        return layer

    app.logger.info('Reading {} from data directory...'.format(layer_name))
    df = get_geobuf(os.path.join(app.config['PEDDATADIR'],
                                 '{}.geobuf'.format(layer_name)))
    app.config[layer_name] = df

    return df


def build_G(sidewalks, crossings, elevator_paths, graph_path):
    # Create graph
    G = network.make_network(sidewalks, crossings, elevator_paths)

    # Serialize to file for posterity
    with open(os.path.join(graph_path), 'wb') as f:
        pickle.dump(G, f)

    return G


def build_G_cached(app):
    # TODO: separate out spatial index from graph creation process to make
    # this simpler?
    G = app.config.get('G', None)

    if G is not None:
        return G

    app.logger.info('Graph or spatial index have not been loaded.')
    datadir = app.config['PEDDATADIR']
    graph_path = os.path.join(datadir, 'graph.pkl')

    # Logic:
    # 1. Attempt to read the spatial index.
    # 2. If reading the spatial index fails, recreate the graph and return.
    # 3. If the spatial index was successfully read, attempt to read the graph.
    # 4. If the graph can't be read, try to create it.

    # Attempt to read existing graph.
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

    app.logger.info('Creating new graph. This may take a few minutes...')

    sidewalks = get_geobuf_cached('sidewalks', app)
    crossings = get_geobuf_cached('crossings', app)
    elevator_paths = get_geobuf_cached('elevator_paths', app)
    G = build_G(sidewalks, crossings, elevator_paths, graph_path)

    app.logger.info('Graph created.')
    app.config['G'] = G

    return G


def build_sindex(G, sindex_path):
    sindex, sindex_list = network.make_sindex(G)
    with open(sindex_path, 'wb') as f:
        pickle.dump(sindex_list, f)

    return sindex


def build_sindex_cached(app):
    # Check if it's already in-memory
    sindex = app.config.get('sindex', None)

    if sindex is not None:
        return sindex

    # TODO: libspatialindex can't do multithreading and the dev team doesn't
    # seem open to updating it. Consider rolling own rtree and/or just use
    # spatialite
    datadir = app.config['PEDDATADIR']
    sindex_path = os.path.join(datadir, 'sindex.pkl')

    # Attempt to read existing spatial index.
    if os.path.exists(sindex_path):
        app.logger.info('Reading spatial index...')
        try:
            with open(sindex_path, 'rb') as f:
                sindex_list = pickle.load(f)
                app.logger.info('Spatial index read.')
                sindex = rtree.index.Index(sindex_list)

                app.config['sindex'] = sindex

                return sindex
        except:
            app.logger.info('Failed to read spatial index.')
    else:
        app.logger.info('No spatial index file found.')

    app.logger.info('Creating new spatial index...')

    G = build_G_cached(app)
    sindex = build_sindex(G, sindex_path)
    app.config['sindex'] = sindex

    app.logger.info('Spatial index created.')

    return sindex
