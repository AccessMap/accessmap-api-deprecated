"""
This script runs the accessmapapi application using a development server.
"""

import os
from accessmapapi.app import app

if __name__ == '__main__':
    os.putenv('LANG', 'en_US.UTF-8')
    os.putenv('LC_ALL', 'en_US.UTF-8')
    HOST = os.environ.get('SERVER_HOST', '0.0.0.0')
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT)
