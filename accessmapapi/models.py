from . import db
import sqlalchemy as sa
import geoalchemy2 as ga


class Sidewalks(db.PublicBase):
    __tablename__ = 'sidewalks'
    id = sa.Column(sa.Integer, primary_key=True)
    geog = sa.Column(ga.Geography)
    incline = sa.Column(sa.Numeric(scale=3))


class Crossings(db.PublicBase):
    __tablename__ = 'crossings'
    id = sa.Column(sa.Integer, primary_key=True)
    geog = sa.Column(ga.Geography)
    incline = sa.Column(sa.Numeric(scale=3))
    curbramps = sa.Column(sa.Boolean)
