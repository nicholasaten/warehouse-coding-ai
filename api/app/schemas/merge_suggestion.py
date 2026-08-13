import uuid
from datetime import datetime

from pydantic import BaseModel


class MergeSuggestionRead(BaseModel):
    id: uuid.UUID
    upload_batch_id: uuid.UUID | None
    row_number: int | None
    warehouse_id: uuid.UUID
    location_type_code: str
    raw_category_rack: str | None
    raw_description: str
    suggested_location_id: uuid.UUID
    similarity_score: float
    reasoning: str
    status: str
    created_at: datetime
    resolved_at: datetime | None

    class Config:
        from_attributes = True
