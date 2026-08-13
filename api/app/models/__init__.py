# Every model module is imported here so Alembic's autogenerate (and anything
# else that walks app.db.base.Base.metadata) sees all of them.
from app.models.category_rack_mapping import CategoryRackMapping
from app.models.location import Location
from app.models.location_type import LocationTypeConfig
from app.models.merge_suggestion import MergeSuggestion
from app.models.raw_import import RawImportBatch, RawLocationSuggestion, RawWarehouseSuggestion
from app.models.recommendation import Recommendation
from app.models.refresh_token import RefreshToken
from app.models.revision import Revision
from app.models.site import Site
from app.models.upload_batch import UploadBatch
from app.models.upload_error import UploadError
from app.models.user import User
from app.models.warehouse import Warehouse
from app.models.warehouse_code import WarehouseCodeConfig
from app.models.warehouse_type import WarehouseTypeConfig

__all__ = [
    "CategoryRackMapping",
    "Location",
    "LocationTypeConfig",
    "MergeSuggestion",
    "RawImportBatch",
    "RawLocationSuggestion",
    "RawWarehouseSuggestion",
    "Recommendation",
    "RefreshToken",
    "Revision",
    "Site",
    "UploadBatch",
    "UploadError",
    "User",
    "Warehouse",
    "WarehouseCodeConfig",
    "WarehouseTypeConfig",
]
