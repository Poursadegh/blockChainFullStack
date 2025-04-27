from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional, List
from .base import BaseSchema, TimestampSchema

class UserBase(BaseSchema):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    role: str = Field(default="user")

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

class UserUpdate(BaseSchema):
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = Field(None, min_length=8)

class UserResponse(UserBase, TimestampSchema):
    id: int
    last_login: Optional[datetime] = None
    login_count: int = Field(default=0)
    kyc_status: str = Field(default="pending")
    liveness_status: str = Field(default="pending")

class UserList(BaseSchema):
    items: List[UserResponse]
    total: int
    page: int
    per_page: int

class LoginRequest(BaseSchema):
    email: EmailStr
    password: str
    remember_me: bool = Field(default=False)

class LoginResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseSchema):
    user_id: int
    email: str
    role: str
    exp: datetime

class PasswordResetRequest(BaseSchema):
    email: EmailStr

class PasswordResetConfirm(BaseSchema):
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8) 