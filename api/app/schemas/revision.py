import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RevisionCreate(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    proposed_value: dict[str, Any]
    comment: str = Field(min_length=1)


class RevisionReject(BaseModel):
    reason: str = Field(min_length=1)


class RevisionEditApprove(BaseModel):
    final_value: dict[str, Any]


class RevisionRead(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    submitted_by: uuid.UUID
    submitted_at: datetime
    original_value: dict[str, Any]
    proposed_value: dict[str, Any]
    comment: str
    status: str
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    rejection_reason: str | None
    final_value: dict[str, Any] | None

    class Config:
        from_attributes = True
