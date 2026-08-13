import uuid

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MeResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    role: str
    site_id: uuid.UUID | None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: MeResponse
