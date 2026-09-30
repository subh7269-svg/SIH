from pydantic import BaseModel
from typing import Optional

class UserLogin(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = "LeadForge Analyst"
    role: Optional[str] = "INVESTIGATOR"

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    full_name: str
    badge_number: str
    is_active: bool

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
