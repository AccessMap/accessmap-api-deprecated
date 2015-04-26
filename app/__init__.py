from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__, instance_relative_config=True)
# FIXME: put user and pass in a config for production
# Get default config (main app dir config.py)


# CORS responses
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers",
                         "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET")

    return response


db = SQLAlchemy(app)

from . import views
