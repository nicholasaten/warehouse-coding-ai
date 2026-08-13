import uuid
from datetime import datetime

from pydantic import BaseModel


class RecommendationRead(BaseModel):
    id: uuid.UUID
    category: str
    warehouse_ids: list[str]
    title: str
    explanation: str
    created_at: datetime

    class Config:
        from_attributes = True
