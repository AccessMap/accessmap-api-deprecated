import geoalchemy2 as ga
import geoalchemy2.functions as func


class ST_MakeEnvelope(ga.functions.GenericFunction):
    name = 'ST_MakeEnvelope'
    type = None


def in_bbox(col, bounds):
    '''Return an SQL condition - whether a geom column intersects a bounding
    box.

    :param col: The column (an SQLAlchemy object).
    :param bounds: A list of bounding-box coordinates in the format
                   [s, w, n, e] - the standard for most systems.
    :type bounds: list

    '''
    envelope = ST_MakeEnvelope(bounds[0], bounds[1], bounds[2], bounds[3],
                               4326)
    return ga.functions.ST_Intersects(col, func.ST_Transform(envelope, 4269))
