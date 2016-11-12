from . import db
import sqlalchemy as sa
import geoalchemy2 as ga


class Sidewalks(db.PublicBase):
    __tablename__ = 'sidewalks'
    id = sa.Column(sa.Integer, primary_key=True)
    geom = sa.Column(ga.Geometry)
    grade = sa.Column(sa.Numeric(scale=3))


class Crossings(db.PublicBase):
    __tablename__ = 'crossings'
    id = sa.Column(sa.Integer, primary_key=True)
    geom = sa.Column(ga.Geometry)
    grade = sa.Column(sa.Numeric(scale=3))
    curbramps = sa.Column(sa.Boolean)


class Curbramps(db.PublicBase):
    __tablename__ = 'curbramps'
    id = sa.Column(sa.Integer, primary_key=True)
    geom = sa.Column(ga.Geometry)


class SidewalksData(db.PublicBase):
    __tablename__ = 'sidewalks_orig'
    id = sa.Column(sa.Integer, primary_key=True)
    geom = sa.Column(ga.Geometry)
    grade = sa.Column(sa.Float)


class CurbrampsData(db.PublicBase):
    __tablename__ = 'curbramps_orig'
    id = sa.Column(sa.Integer, primary_key=True)
    geom = sa.Column(ga.Geometry)
