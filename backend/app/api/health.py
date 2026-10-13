from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import time

from app.core.database import get_session_dependency
from app.core.auth import get_current_user_optional, require_operator
from app.core.config import settings
from app.services import get_router
from app.models import Provider

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    environment: str
    demo_mode: bool


class ReadyResponse(BaseModel):
    status: str
    database: bool
    providers_loaded: int
    providers_healthy: int


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        environment=settings.app_env,
        demo_mode=settings.demo_mode and settings.app_env == "development",
    )


@router.get("/ready", response_model=ReadyResponse)
async def ready(session: AsyncSession = Depends(get_session_dependency)):
    db_ok = False
    try:
        await session.execute(select(1))
        db_ok = True
    except Exception:
        pass

    router = await get_router(session)
    providers_loaded = len(router.get_provider_ids())
    health_results = await router.health_check_all()
    providers_healthy = sum(1 for r in health_results.values() if r["healthy"])

    return ReadyResponse(
        status="ready" if db_ok and providers_loaded > 0 else "not_ready",
        database=db_ok,
        providers_loaded=providers_loaded,
        providers_healthy=providers_healthy,
    )


@router.get("/version")
async def version():
    return {"version": "1.0.0", "name": "sentinel-foundry"}