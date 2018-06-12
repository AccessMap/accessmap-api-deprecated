'''The flask application package.'''
from flask import Flask, g
import json
import logging
import os
from accessmapapi import db

with open('./layers.json') as f:
    config = json.load(f)


# Set up the app
def create_app():
    app = Flask(__name__)

    # Set up the configuration data
    if 'PEDDATADIR' in os.environ:
        datadir = os.environ['PEDDATADIR']
    else:
        datadir = os.path.join(os.path.dirname(__file__), '../data')
        datadir = os.path.abspath(datadir)
    app.config['PEDDATADIR'] = datadir

    # To get debugging messages:
    app.config['PROPAGATE_EXCEPTIONS'] = True

    # Set up logging
    formatter = logging.Formatter(
        '[%(levelname)s] %(message)s'
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    @app.before_request
    def before_request():
        # Create a db connection
        try:
            g.db = db.database
            g.db.connect()
            # Enable spatialite extension
            g.db.load_module('mod_spatialite.so')
        except:
            # TODO: Catch a useful exception?
            pass
        g.layers = config

    @app.after_request
    def after_request(response):
        # Tear down db connection
        g.db.close()

        # CORS responses
        # TODO: Add some kind of control on access?
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers",
                             "Content-Type,Authorization")
        response.headers.add("Access-Control-Allow-Methods", "GET")

        return response

    return app

app = create_app()


import accessmapapi.views  # noqa: F401
