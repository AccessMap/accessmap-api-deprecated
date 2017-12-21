from flask import g
import geopandas as gpd
import os
from accessmapapi import app, network


def get_sidewalks():
    sidewalks = getattr(g, 'sidewalks', None)
    if sidewalks is None:
        datadir = app.config['PEDDATADIR']
        gdf = gpd.read_file(os.path.join(datadir, 'sidewalks.geojson'))
        sidewalks = gdf
        g.sidewalks = gdf

    return sidewalks


def get_crossings():
    crossings = getattr(g, 'crossings', None)
    if crossings is None:
        datadir = app.config['PEDDATADIR']
        gdf = gpd.read_file(os.path.join(datadir, 'crossings.geojson'))
        crossings = gdf
        g.crossings = gdf

    return crossings


def get_network():
    sidewalks = get_sidewalks()
    crossings = get_crossings()
    G = getattr(g, 'network', None)
    if G is None:
        g.network = G = network.make_network(sidewalks, crossings)

    return G
