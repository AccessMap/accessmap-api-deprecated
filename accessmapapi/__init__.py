from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL

app = Flask(__name__, instance_relative_config=True)
app.config.from_object("config")
# Get instance config (hidden from git, is in app dir/instance/config.py)
try:
    app.config.from_pyfile("config.py")
except IOError:
    pass
# FIXME: put user and pass in a config for production
# Get default config (main app dir config.py)

# Enables debug traceback for logging
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


conn_url = URL('postgresql', app.config['DB_USER'], app.config['DB_PASS'],
               app.config['DB_HOST'], app.config['DB_PORT'],
               app.config['DB_NAME'])

engine = create_engine(conn_url, convert_unicode=True)

from . import urls
