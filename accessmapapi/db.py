import os
from playhouse.sqlite_ext import SqliteExtDatabase

DATADIR = os.path.abspath(os.path.join(os.path.realpath(__file__),
                                       '../../data'))
DBDIR = os.environ.get('PEDDATADIR', DATADIR)
DBPATH = os.path.join(DBDIR, 'graph.db')
BUILDPATH = os.path.join(DBDIR, 'build.db')

database = SqliteExtDatabase(DBPATH)
if os.path.exists(BUILDPATH):
    # Build DB gets recreated on every launch
    os.remove(BUILDPATH)
database_build = SqliteExtDatabase(BUILDPATH)


# Set up for spatialite stuff
print('Setting up spatialite')
database.load_extension('mod_spatialite.so')
database_build.load_extension('mod_spatialite.so')
print('Done')
