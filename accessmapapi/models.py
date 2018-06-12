from peewee import Field, Model
from peewee import BigIntegerField, CharField, DecimalField, DoubleField
from peewee import fn
# from peewee import JSONField
from accessmapapi import db


# TODO: add db_value and python_value methods
class GeometryField(Field):
    field_type = 'geometry'


COL_MAP = {
    'decimal': DecimalField,
    'integer': BigIntegerField,
    'real': DoubleField,
    'varchar': CharField,
    'geometry': GeometryField,
}


class BaseModel(Model):
    class Meta:
        database = db.database


class Node(BaseModel):
    coord = CharField(index=True)


def edge_factory(cols, name='Edges'):
    coldict = {}
    for col, coltype in cols.items():
        coldict[col] = COL_MAP[coltype](null=True)
    Edges = type(name, (BaseModel, ), coldict)

    return Edges
