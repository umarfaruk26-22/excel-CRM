from pydantic import BaseModel, Field
from typing import Optional

class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str

class AdminOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = "Administrator"
    is_active: bool

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    admin: AdminOut

class UpdateProfileRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150)
    email: str = Field(..., min_length=3, max_length=255)

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)
