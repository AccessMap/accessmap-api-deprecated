from flask_restful import Api

from accessmapapi import app

from accessmapapi.views.v1.curbramps import CurbrampsV1
from accessmapapi.views.v1.sidewalks import SidewalksV1

from accessmapapi.views.v2.crossings import CrossingsV2
from accessmapapi.views.v2.sidewalks import SidewalksV2

api = Api(app)

# API v1
api.add_resource(CurbrampsV1, '/v1/curbramps.geojson')
api.add_resource(SidewalksV1, '/v1/sidewalks.geojson')

# API v2
api.add_resource(SidewalksV2, '/v2/sidewalks.geojson')
api.add_resource(CrossingsV2, '/v2/crossings.geojson')
