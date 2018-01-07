import geopandas as gpd
import os
import pickle
import rtree
from accessmapapi import app, network


def get_sidewalks():
    sidewalks = app.config.get('sidewalks', None)
    if sidewalks is not None:
        return sidewalks

    app.logger.info('Reading sidewalks from data directory...')
    datadir = app.config['PEDDATADIR']
    sidewalks = gpd.read_file(os.path.join(datadir, 'sidewalks.geojson'))
    app.config['sidewalks'] = sidewalks

    return sidewalks


def get_crossings():
    crossings = app.config.get('crossings', None)
    if crossings is not None:
        return crossings

    app.logger.info('Reading crossings from data directory...')
    datadir = app.config['PEDDATADIR']
    crossings = gpd.read_file(os.path.join(datadir, 'crossings.geojson'))
    app.config['crossings'] = crossings

    return crossings


def get_G():
    # TODO: separate out spatial index from graph creation process to make
    # this simpler?
    G = app.config.get('G', None)
    sindex = app.config.get('sindex', None)

    if (G is not None) and (sindex is not None):
        return G, sindex

    sidewalks = get_sidewalks()
    crossings = get_crossings()

    datadir = app.config['PEDDATADIR']
    graph_path = os.path.join(datadir, 'graph.txt')
    sindex_path = os.path.join(datadir, 'graph_sindex')

    failed = False

    if not G:
        # Attempt to read it in.
        if os.path.exists(graph_path):
            app.logger.info('Reading graph...')
            # Try to recover a previously-created graph, if possible
            try:
                with open(graph_path, 'rb') as f:
                    G = pickle.load(f)
                    app.logger.info('Read graph.')
            except:
                app.logger.info('Failed to read graph...')
                failed = True
        else:
            app.logger.info('No graph file found.')
            failed = True

    if not sindex:
        if os.path.exists('{}{}'.format(sindex_path, '.idx')):
            app.logger.info('Reading spatial index...')
            # Try to recover a previously-created graph, if possible
            try:
                sindex = rtree.index.Index(sindex_path)
                app.logger.info('Read spatial index.')
            except:
                app.logger.info('Failed to read spatial index...')
                os.remove(sindex_path)
                failed = True
        else:
            app.logger.info('No spatial index found.')
            failed = True

    if failed:
        # Create graph
        app.logger.info('Creating new graph. This may take a few minutes...')
        G, sindex = network.make_network(sidewalks, crossings, sindex_path)

        # Serialize to file for posterity
        with open(os.path.join(datadir, 'graph.txt'), 'wb') as f:
            pickle.dump(G, f)

    app.config['G'] = G
    app.config['sindex'] = sindex

    return G, sindex
