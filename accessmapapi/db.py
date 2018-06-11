import os
from playhouse.sqlite_ext import SqliteExtDatabase

DATADIR = os.path.abspath(os.path.join(os.path.realpath(__file__),
                                       '../../data'))
DBDIR = os.environ.get('PEDDATADIR', DATADIR)
DBPATH = os.path.join(DBDIR, 'graph.db')

database = SqliteExtDatabase(DBPATH)


# Set up for spatialite stuff
print('Setting up spatialite')
database.load_extension('mod_spatialite.so')
print('Done')
