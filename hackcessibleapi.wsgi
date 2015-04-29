import sys
sys.path.insert(0, '/var/www/sites/hackcessibleapi/')
activate_this = '/var/www/sites/hackcessibleapi/venv/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))


from manage import app as application
