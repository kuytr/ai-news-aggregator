"""
schemas/user.py - Pydantic schemas for User data validation.
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime


class UserRegister(BaseModel):
    """Schema for user registration."""
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class OTPVerify(BaseModel):
    """Schema for OTP verification."""
    email: EmailStr
    otp: str


class UserResponse(BaseModel):
    """Schema for user data returned from API."""
    id: int
    username: str
    email: str
    is_verified: bool
    preferred_categories: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class PreferenceUpdate(BaseModel):
    """Schema for updating user category preferences."""
    categories: List[str]
