import uuid
from datetime import datetime

from pydantic import BaseModel


class UploadBatchRead(BaseModel):
    id: uuid.UUID
    file_type: str
    file_name: str
    row_count: int
    success_count: int
    error_count: int
    pending_count: int
    status: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class UploadErrorRead(BaseModel):
    row_number: int
    column_name: str
    error_message: str

    class Config:
        from_attributes = True
