'''The flask application package.'''
from flask import Flask
import logging
import os


# Set up the app
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
@app.before_first_request
def setup_logging():
    formatter = logging.Formatter(
        '[%(levelname)s] %(message)s'
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


# CORS responses
# FIXME: re-enable CORS soon
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers",
                         "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET")
    return response

import accessmapapi.views  # noqa: F401
