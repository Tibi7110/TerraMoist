"""Pydantic models for authentication flows."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class UserPublic(BaseModel):
    """Safe user data returned to the frontend."""

    id: int
    name: str
    email: str


class AuthResponse(BaseModel):
    """Standard response for successful register/login/me calls."""

    token: str
    user: UserPublic


class RegisterRequest(BaseModel):
    """Body of POST /api/v1/auth/register."""

    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Name must be at least 2 characters long")
        return value

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("Email address is invalid")
        return value


class LoginRequest(BaseModel):
    """Body of POST /api/v1/auth/login."""

    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return value.strip().lower()
