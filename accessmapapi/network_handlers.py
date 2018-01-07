import geopandas as gpd
import os
import pickle
import rtree
from accessmapapi import network


def get_sidewalks(app):
    sidewalks = app.config.get('sidewalks', None)
    if sidewalks is not None:
        return sidewalks

    app.logger.info('Reading sidewalks from data directory...')
    datadir = app.config['PEDDATADIR']
    sidewalks = gpd.read_file(os.path.join(datadir, 'sidewalks.geojson'))
    app.config['sidewalks'] = sidewalks

    return sidewalks


def get_crossings(app):
    crossings = app.config.get('crossings', None)
    if crossings is not None:
        return crossings

    app.logger.info('Reading crossings from data directory...')
    datadir = app.config['PEDDATADIR']
    crossings = gpd.read_file(os.path.join(datadir, 'crossings.geojson'))
    app.config['crossings'] = crossings

    return crossings


def get_G(app):
    # TODO: separate out spatial index from graph creation process to make
    # this simpler?
    G = app.config.get('G', None)
    sindex = app.config.get('sindex', None)

    if (G is not None) and (sindex is not None):
        return G, sindex

    app.logger.info('Graph or spatial index have not been loaded.')

    sidewalks = get_sidewalks(app)
    crossings = get_crossings(app)

    datadir = app.config['PEDDATADIR']
    sindex_path = os.path.join(datadir, 'graph_sindex')
    graph_path = os.path.join(datadir, 'graph.txt')

    # Logic:
    # 1. Attempt to read the spatial index.
    # 2. If reading the spatial index fails, recreate the graph and return.
    # 3. If the spatial index was successfully read, attempt to read the graph.
    # 4. If the graph can't be read, try to create it.

    def make_graph():
        # Create graph
        app.logger.info('Creating new graph. This may take a few minutes...')

        os.remove('{}{}'.format(sindex_path, '.idx'))
        os.remove('{}{}'.format(sindex_path, '.dat'))

        G, sindex = network.make_network(sidewalks, crossings, sindex_path)

        # Serialize to file for posterity
        with open(os.path.join(datadir, 'graph.txt'), 'wb') as f:
            pickle.dump(G, f)

        app.logger.info('Graph created.')

        return G, sindex

    rebuilt = False

    # FIXME: this is overly complicated. Abstract + simplify
    if sindex is None:
        if os.path.exists('{}{}'.format(sindex_path, '.idx')):
            app.logger.info('Attempting to read spatial index...')
            try:
                sindex = rtree.index.Index(sindex_path)
                app.logger.info('Read spatial index.')
            except:
                app.logger.info('Failed to read spatial index.')
                G, sindex = make_graph()
                rebuilt = True
        else:
            app.logger.info('No spatial index found.')
            G, sindex = make_graph()
            rebuilt = True

    if not rebuilt and G is None:
        # Attempt to read it in.
        if os.path.exists(graph_path):
            app.logger.info('Reading graph...')
            try:
                with open(graph_path, 'rb') as f:
                    G = pickle.load(f)
                    app.logger.info('Read graph.')
            except:
                app.logger.info('Failed to read graph...')
                G, sindex = make_graph()
        else:
            app.logger.info('No graph file found.')
            G, sindex = make_graph()

    app.config['G'] = G
    app.config['sindex'] = sindex

    return G, sindex
