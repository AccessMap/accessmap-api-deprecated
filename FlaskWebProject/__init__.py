'''The flask application package.'''
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry
import os


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy()


import FlaskWebProject.views
