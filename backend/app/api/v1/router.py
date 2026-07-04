"""
FastAPI APIRouter registration v1 module.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.msme import router as msme_router
from app.api.v1.endpoints.score import router as score_router
from app.api.v1.endpoints.consent import router as consent_router
from app.api.v1.endpoints.ecosystem import router as ecosystem_router
from app.api.v1.endpoints.portfolio import router as portfolio_router

router = APIRouter()

# Register endpoint routers
router.include_router(auth_router)
router.include_router(msme_router)
router.include_router(score_router)
router.include_router(consent_router)
router.include_router(ecosystem_router)
router.include_router(portfolio_router)
