from flask_restful import Api

from app import app

api = Api(app)

# API v1
from app.views.v1.curbramps import CurbrampsV1
from app.views.v1.sidewalks import SidewalksV1
api.add_resource(CurbrampsV1, '/v1/curbramps.geojson')
api.add_resource(SidewalksV1, '/v1/sidewalks.geojson')

# API v2
from app.views.v2.crossings import CrossingsV2
from app.views.v2.sidewalks import SidewalksV2
# api.add_resource(curbrampsv1.CurbrampsAPI, '/v2/curbramps-data.geojson')
# api.add_resource(sidewalksv1.SidewalksAPI, '/v2/sidewalks-data.geojson')
api.add_resource(SidewalksV2, '/v2/sidewalks.geojson')
api.add_resource(CrossingsV2, '/v2/crossings.geojson')
