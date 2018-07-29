'''Module containing transportation network (initial graph) build functions'''
import os
import sys

from peewee import fn, DoubleField
from shapely.geometry import shape

from accessmapapi.constants import PRECISION
from accessmapapi.build.featuresource import FeatureSource
from accessmapapi.models import GeometryField, Node, edge_factory
from accessmapapi.utils import haversine


def trans_network(layer_config, db):
    '''Create an initial transportation network as sqlite tables from a stream
    of incoming ways. The ways can be either a stream or just any iterable
    containing appropriate GeoJSON features.

    :param ways: An iterable of GeoJSON LineString features.
    :type ways: An iterable of GeoJSON LineString features.

    '''
    # TODO: either relax constraint of uniqueness on geometries or dedupe prior to
    # adding data - this causes first attempt at building to always fail

    columns = {}
    sources = []
    for name, layer in layer_config.items():
        source = FeatureSource(layer['path'], name, layer['properties'])
        sources.append(source)
        # TODO: check for incompatible column definitions
        columns = {**columns, **source.properties}

    # Hard-code these required rows
    cols = {k: v['type'] for k, v in columns.items()}
    cols['way'] = 'varchar'
    cols['u'] = 'integer'
    cols['v'] = 'integer'
    cols['forward'] = 'integer'

    # Create the edge and nodes table
    try:
        db.connect()
    except:
        pass
    Edge = edge_factory(cols, 'edges')
    Edge._meta.database = db
    Node._meta.database = db
    modlist = [Edge, Node]
    db.drop_tables(modlist)
    Edge.add_index('u')
    Edge.add_index('v')
    # Add covering index - essentially copies the whole table, but should double u query
    # speed?
    rest = [c for c in Edge._meta.sorted_field_names if c not in ['u', 'v']]
    Edge.add_index('u', 'v', *rest, name='edge_covering_index')
    db.create_tables(modlist)

    # Enable spatialite and set up geom tables / info
    db.load_extension('mod_spatialite.so')
    db.execute_sql('SELECT InitSpatialMetaData(1)')

    # Add the geometry column
    sql = "SELECT AddGeometryColumn('edges', 'geometry', 4326, 'LINESTRING')"
    db.execute_sql(sql)
    Edge._meta.add_field('geometry', GeometryField())

    # Add the length column
    Edge._meta.add_field('length', DoubleField())

    def record_to_edge(record, way):
        geometry = record['geometry']
        u = str([round(coord, PRECISION) for coord in geometry['coordinates'][0]])
        v = str([round(coord, PRECISION) for coord in geometry['coordinates'][-1]])
        # Calculate length - ignore any 'length' property that comes with record
        length = haversine(geometry['coordinates'])
        return {
            **record['properties'],
            'way': way,
            'u': u,
            'v': v,
            'geometry': fn.ST_GeomFromText(shape(geometry).wkt),
            'length': length,
        }

    i = 0
    with db.atomic():
        for source in sources:
            for record in source:
                message = '\r    {} edges imported to db'.format(i)
                sys.stdout.write(message)
                sys.stdout.flush()
                i += 1

                edge_data = record_to_edge(record, source.waytype)
                edge_data['forward'] = 1

                # Flip the geometry for the reverse direction
                coords = reversed(record['geometry']['coordinates'])
                record['geometry']['coordinates'] = list(coords)

                edge_data_rev = record_to_edge(record, source.waytype)
                for k, v in columns.items():
                    if k in edge_data_rev:
                        if 'inverts' in v and v['inverts']:
                            edge_data_rev[k] = -1 * edge_data_rev[k]
                edge_data_rev['forward'] = 0

                for node in ['u', 'v']:
                    query = 'SELECT rowid FROM node WHERE coord = ?'
                    cursor = db.execute_sql(query, (edge_data[node],))
                    rows = cursor.fetchall()
                    if not rows:
                        n = Node.create(coord=edge_data[node])
                        node_new = n.id
                    else:
                        node_new = rows[0][0]

                    edge_data[node] = node_new
                    if node == 'u':
                        edge_data_rev['v'] = node_new
                    else:
                        edge_data_rev['u'] = node_new

                Edge.create(**edge_data)
                Edge.create(**edge_data_rev)
        print()

        # Add a spatial index
        print('Creating spatial index...')
        sql = "SELECT CreateSpatialIndex('edges', 'geometry')"
        db.execute_sql(sql)
        print('Done')

    # The 'build' table was successfully created - replace the main one!
    os.rename('./data/build.db', './data/graph.db')
