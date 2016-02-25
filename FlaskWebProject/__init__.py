'''The flask application package.'''
from flask import Flask
import os


app = Flask(__name__)
app.config['DATABASE_URL'] = os.environ['DATABASE_URL']
app.config['MAPBOX_TILES'] = os.environ['MAPBOX_TILES']
app.config['MAPBOX_TOKEN'] = os.environ['MAPBOX_TOKEN']
# To get debugging messages:
app.config['PROPAGATE_EXCEPTIONS'] = True


# CORS responses
# FIXME: re-enable CORS soon
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers",
                         "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET")

    return response

import FlaskWebProject.views
