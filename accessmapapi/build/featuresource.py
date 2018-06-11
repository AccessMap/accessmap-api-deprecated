'''"feature source" class: organizes feature inputs into single, streamable
object with input filtering and property definitions.'''
from collections import Iterator
import geobuf
import fiona
from accessmapapi.constants import WAY_PROPERTIES


class FeatureSource(Iterator):
    def __init__(self, path, waytype, properties=WAY_PROPERTIES):
        self.path = path
        self.waytype = waytype
        self.properties = properties
        if path.endswith('.geobuf'):
            with open(path, 'rb') as f:
                self.collection = iter(geobuf.decode(f.read())['features'])
        else:
            self.collection = fiona.open(path, 'r')

    def _filter(self, record):
        # TODO: property value type checking / coercing from properties map
        props = {}
        for k, v in record['properties'].items():
            if k in self.properties:
                props[k] = v
        return {
            'geometry': record['geometry'],
            'properties': props,
        }

    def __next__(self):
        try:
            record = next(self.collection)
        except StopIteration:
            # Is this redundant?
            raise StopIteration

        return self._filter(record)
