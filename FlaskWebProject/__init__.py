'''The flask application package.'''
from flask import Flask
import os


app = Flask(__name__)
app.config['DATABASE_URL'] = os.environ['DATABASE_URL']
# To get debugging messages:
app.config['PROPAGATE_EXCEPTIONS'] = True


import FlaskWebProject.views
