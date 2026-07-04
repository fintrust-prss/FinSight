"""
FastAPI dependencies for v1 API routes.

Provides:
  - get_db: Database session injection
  - get_current_user: JWT token authentication and claim extraction
  - require_role: Role-Based Access Control (RBAC) guard
  - check_consent: AA Consent compliance validation gating alternate data endpoints
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncGenerator

import structlog
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import ConsentRecord
from app.db.session import async_session_factory

logger = structlog.get_logger(__name__)
security = HTTPBearer()
settings = get_settings()


# ===========================================================================
# Database Dependency
# ===========================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding an async database session per request.

    Transactions are rolled back automatically on error; committed on success.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ===========================================================================
# Security & JWT Authentication
# ===========================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Dependency checking JWT token authenticity in the Authorization header.

    Returns the claims dict (sub, role, etc.) if token is valid.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key or "demo_fallback_secret",  # fallback in development
            algorithms=[settings.jwt_algorithm],
        )
        username: str | None = payload.get("sub")
        role: str | None = payload.get("role")
        
        if username is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims. Subject and Role are required.",
            )
        return payload
    except JWTError as e:
        logger.warning("jwt_verification_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


class RoleChecker:
    """Role-Based Access Control route guard."""

    def __init__(self, allowed_roles: list[str]) -> None:
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role")
        if user_role not in self.allowed_roles:
            logger.warning(
                "rbac_authorization_denied",
                user=current_user.get("sub"),
                role=user_role,
                required=self.allowed_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for your security role.",
            )
        return current_user


# ===========================================================================
# Consent-Gating Compliance Guard
# ===========================================================================

async def check_consent(
    msme_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(get_current_user),
) -> None:
    """
    Consent compliance guard.
    Gating criteria (Section 9): Checks that an ACTIVE, unexpired consent record
    exists for the requested msme_id.
    """
    now = datetime.now(timezone.utc)
    
    # Query active consent records in the DB
    # We check status == "ACTIVE" and expiry > now
    stmt = (
        select(ConsentRecord)
        .where(
            ConsentRecord.msme_id == msme_id,
            ConsentRecord.status == "ACTIVE",
        )
        .order_by(ConsentRecord.expiry.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    consent = result.scalars().first()

    # If consent doesn't exist, has expired, or is revoked, block access
    # We handle timezone conversion for comparison
    if not consent or consent.expiry.replace(tzinfo=timezone.utc) < now:
        logger.warning("consent_gating_blocked_request", msme_id=msme_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Access Forbidden. Active Account Aggregator consent is required "
                "to retrieve this alternate credit data."
            ),
        )
