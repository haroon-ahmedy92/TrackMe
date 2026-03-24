from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=8, max_length=200)


class AuthUserProfile(BaseModel):
    id: str
    full_name: str
    email: str
    role: str
    tenant_id: str


class LoginResponse(BaseModel):
    access_token: str
    profile: AuthUserProfile
