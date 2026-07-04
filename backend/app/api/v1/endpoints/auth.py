"""
Authentication Endpoints — JWT Token Generation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from pydantic import BaseModel, Field

from app.config import get_settings

router = APIRouter(tags=["Authentication"])
settings = get_settings()


class TokenRequest(BaseModel):
    """User credentials request parameters."""
    username: str = Field(..., example="bank_officer_sharma")
    role: Literal["bank_officer", "underwriter", "admin"] = Field("bank_officer", example="bank_officer")


class TokenResponse(BaseModel):
    """Access token payload response envelope."""
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_in_seconds: int


@router.post(
    "/auth/token",
    response_model=TokenResponse,
    summary="Issue demo authentication token",
    response_description="Returns Bearer token with associated RBAC claims",
)
def issue_token(payload: TokenRequest) -> dict:
    """
    Demo login. Generates JWT access token with selected role claim.
    No database credential check is enforced (designed for hackathon sandbox login).
    """
    secret_key = settings.jwt_secret_key or "demo_fallback_secret"
    expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    expire_timestamp = datetime.now(timezone.utc) + expires_delta

    claims = {
        "sub": payload.username,
        "role": payload.role,
        "exp": expire_timestamp,
    }
    
    encoded_jwt = jwt.encode(
        claims,
        secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return {
        "access_token": encoded_jwt,
        "token_type": "bearer",
        "role": payload.role,
        "expires_in_seconds": int(expires_delta.total_seconds()),
    }
