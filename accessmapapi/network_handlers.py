from flask import current_app
import geopandas as gpd
import os
import pickle
import rtree
from accessmapapi import app, cache, network


def get_sidewalks():
    sidewalks = cache.get('sidewalks')
    if sidewalks:
        return sidewalks

    print('Reading sidewalks from data directory...')
    datadir = app.config['PEDDATADIR']
    sidewalks = gpd.read_file(os.path.join(datadir, 'sidewalks.geojson'))
    cache.set('sidewalks', sidewalks)

    return sidewalks


def get_crossings():
    crossings = cache.get('crossings')
    if crossings:
        return crossings

    print('Reading crossings from data directory...')
    datadir = app.config['PEDDATADIR']
    crossings = gpd.read_file(os.path.join(datadir, 'crossings.geojson'))
    cache.set('crossings', crossings)

    return crossings


def get_G():
    # TODO: separate out spatial index from graph creation process to make
    # this simpler?
    G = cache.get('G')
    sindex = cache.get('sindex')

    if G and sindex:
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
            print('Reading graph...')
            # Try to recover a previously-created graph, if possible
            try:
                with open(graph_path, 'rb') as f:
                    G = pickle.load(f)
                    print('Done')
            except:
                print('Failed to read graph...')
                failed = True
        else:
            print('No graph file found.')
            failed = True

    if not sindex:
        if os.path.exists('{}{}'.format(sindex_path, '.idx')):
            print('Reading spatial index...')
            # Try to recover a previously-created graph, if possible
            try:
                sindex = rtree.index.Index(sindex_path)
                print('Done')
            except:
                print('Failed to read spatial index...')
                os.remove(sindex_path)
                failed = True
        else:
            print('No spatial index found.')
            failed = True

    if failed:
        # Create graph
        print('Creating new graph + index. This may take a few minutes...')
        G, sindex = network.make_network(sidewalks, crossings, sindex_path)

        # Serialize to file for posterity
        with open(os.path.join(datadir, 'graph.txt'), 'wb') as f:
            pickle.dump(G, f)

    cache.set('G', G)
    cache.set('sindex', sindex)

    return G, sindex
