from sqlalchemy import MetaData, Table, Column, Integer, Float
from geoalchemy2 import Geometry


from accessmapapi import engine

meta = MetaData()

# (Raw) curbramps table
curbramps_data = Table('curbramps_data', meta,
                       Column('id', Integer, primary_key=True),
                       Column('geom', Geometry))

# (Raw) sidewalks table
sidewalks_data = Table('sidewalks_data', meta,
                       Column('id', Integer, primary_key=True),
                       Column('geom', Geometry),
                       Column('grade', Float))


# (Clean) sidewalks table
sidewalks = Table('sidewalks', meta,
                  Column('id', Integer, primary_key=True),
                  Column('geom', Geometry),
                  Column('grade', Float))

# (Clean) crossings table
crossings = Table('crossings', meta,
                  Column('id', Integer, primary_key=True),
                  Column('geom', Geometry),
                  Column('grade', Float))
