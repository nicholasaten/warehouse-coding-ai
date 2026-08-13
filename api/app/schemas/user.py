import uuid

from pydantic import BaseModel, EmailStr, model_validator


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: str  # "admin" | "pic"
    site_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _site_id_matches_role(self) -> "UserCreate":
        if self.role == "pic" and self.site_id is None:
            raise ValueError("site_id is required when role is 'pic'")
        if self.role == "admin" and self.site_id is not None:
            raise ValueError("site_id must be omitted when role is 'admin'")
        return self


class UserRead(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    role: str
    site_id: uuid.UUID | None
    is_active: bool

    class Config:
        from_attributes = True
