from sqlalchemy import MetaData, Table, Column, Integer, Numeric
from geoalchemy2 import Geometry
from app import engine


meta = MetaData()

# (Raw) curbramps table
raw_curbramps = Table('curbramps', meta,
                      Column('id', Numeric, primary_key=True),
                      Column('geom', Geometry),
                      schema='data')

# (Raw) sidewalks table
raw_sidewalks = Table('sidewalks', meta,
                      Column('id', Integer, primary_key=True),
                      Column('geom', Geometry),
                      schema='data')

# raw_curbramps = Table('curbramps', meta, schema='data', autoload=True,
#                       autoload_with=engine)
#
# # (Raw) sidewalks table
# raw_sidewalks = Table('sidewalks', meta, schema='data', autoload=True,
#                       autoload_with=engine)
#
# # (Clean) sidewalks table
# sidewalks = Table('sidewalks', meta, autoload=True, autoload_with=engine)
#
# # (Clean) crossings table
# crossings = Table('crossings', meta, autoload=True, autoload_with=engine)
