from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
import logging

from app.core.database import get_session_dependency
from app.core.auth import get_current_user, require_operator, audit_log
from app.models import Provider
from app.services import get_router

router = APIRouter(prefix="/api/v1/providers", tags=["providers"])

logger = logging.getLogger(__name__)




class ProviderUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[str] = Field(None, pattern="^(openai-compatible|anthropic|gemini|ollama)$")
    base_url: Optional[str] = Field(None, min_length=1, max_length=500)
    api_key: Optional[str] = Field(None, max_length=500)
    model: Optional[str] = Field(None, max_length=200)
    enabled: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=-100, le=100)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300)
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    extra_config: Optional[dict] = None


class ProviderResponse(BaseModel):
    id: str
    name: str
    type: str
    base_url: str
    api_key: Optional[str] = None
    model: Optional[str]
    enabled: bool
    priority: int
    timeout_seconds: int
    max_retries: int
    extra_config: Optional[dict]
    created_at: str
    updated_at: str
    health: Optional[dict] = None

    class Config:
        from_attributes = True


class ProviderHealthResponse(BaseModel):
    provider_id: str
    healthy: bool
    latency_ms: Optional[int]
    error: Optional[str]
    circuit_open: bool
    consecutive_failures: int


class ProviderTestResponse(BaseModel):
    success: bool
    latency_ms: Optional[int] = None
    error: Optional[str] = None
    models: List[str] = []


class PaginatedProviders(BaseModel):
    items: List[ProviderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ProviderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(openai-compatible|anthropic|gemini|ollama)$")
    base_url: HttpUrl
    api_key: Optional[str] = Field(None, max_length=500)
    model: Optional[str] = Field(None, max_length=200)
    enabled: bool = True
    priority: int = Field(0, ge=-100, le=100)
    timeout_seconds: int = Field(30, ge=1, le=300)
    max_retries: int = Field(2, ge=0, le=10)
    extra_config: Optional[dict] = None


class ProviderUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[str] = Field(None, pattern="^(openai-compatible|anthropic|gemini|ollama)$")
    base_url: Optional[HttpUrl] = None
    api_key: Optional[str] = Field(None, max_length=500)
    model: Optional[str] = Field(None, max_length=200)
    enabled: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=-100, le=100)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300)
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    extra_config: Optional[dict] = None


@router.get("", response_model=PaginatedProviders)
async def list_providers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    enabled: Optional[bool] = Query(None),
    user: dict = Depends(require_operator),
    session: AsyncSession = Depends(get_session_dependency),
):
    query = select(Provider)
    if enabled is not None:
        query = query.where(Provider.enabled == enabled)
    query = query.order_by(desc(Provider.priority), Provider.created_at)

    total_result = await session.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    providers = result.scalars().all()

    router = await get_router(session)
    health_results = await router.health_check_all()

    items = []
    for p in providers:
        health = health_results.get(p.id, {})
        items.append(ProviderResponse(
            id=p.id,
            name=p.name,
            type=p.type,
            base_url=p.base_url,
            api_key="***" if p.api_key else None,
            model=p.model,
            enabled=p.enabled,
            priority=p.priority,
            timeout_seconds=p.timeout_seconds,
            max_retries=p.max_retries,
            extra_config=p.extra_config,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
            health=health,
        ))

    return PaginatedProviders(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    data: ProviderCreate,
    user: dict = Depends(require_operator),
    session: AsyncSession = Depends(get_session_dependency),
):
    existing = await session.execute(select(Provider).where(Provider.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Provider name already exists")

    provider = Provider(**data.model_dump(mode='json'))
    session.add(provider)
    await session.flush()

    await audit_log(session, user.sub, "create_provider", "provider", provider.id, data.model_dump(mode='json'))

    router = await get_router(session)
    await router.reload()

    health_results = await router.health_check_all()
    health = health_results.get(provider.id, {})

    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        type=provider.type,
        base_url=provider.base_url,
        api_key="***" if provider.api_key else None,
        model=provider.model,
        enabled=provider.enabled,
        priority=provider.priority,
        timeout_seconds=provider.timeout_seconds,
        max_retries=provider.max_retries,
        extra_config=provider.extra_config,
        created_at=provider.created_at.isoformat(),
        updated_at=provider.updated_at.isoformat(),
        health=health,
    )


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: str,
    user: dict = Depends(require_operator),
    session: AsyncSession = Depends(get_session_dependency),
):
    result = await session.execute(select(Provider).where(Provider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    router = await get_router(session)
    health_results = await router.health_check_all()
    health = health_results.get(provider_id, {})

    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        type=provider.type,
        base_url=provider.base_url,
        api_key="***" if provider.api_key else None,
        model=provider.model,
        enabled=provider.enabled,
        priority=provider.priority,
        timeout_seconds=provider.timeout_seconds,
        max_retries=provider.max_retries,
        extra_config=provider.extra_config,
        created_at=provider.created_at.isoformat(),
        updated_at=provider.updated_at.isoformat(),
        health=health,
    )


@router.patch("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: str,
    data: ProviderUpdate,
    user: dict = Depends(require_operator),
    session: AsyncSession = Depends(get_session_dependency),
):
    result = await session.execute(select(Provider).where(Provider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    update_data = data.model_dump(exclude_unset=True, mode='json')
    for key, value in update_data.items():
        setattr(provider, key, value)

    await session.flush()
    await audit_log(session, user.sub, "update_provider", "provider", provider_id, data.model_dump(exclude_unset=True, mode='json'))

    router = await get_router(session)
    await router.reload()

    health_results = await router.health_check_all()
    health = health_results.get(provider_id, {})

    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        type=provider.type,
        base_url=provider.base_url,
        api_key="***" if provider.api_key else None,
        model=provider.model,
        enabled=provider.enabled,
        priority=provider.priority,
        timeout_seconds=provider.timeout_seconds,
        max_retries=provider.max_retries,
        extra_config=provider.extra_config,
        created_at=provider.created_at.isoformat(),
        updated_at=provider.updated_at.isoformat(),
        health=health,
    )


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: str,
    user: dict = Depends(require_operator),
    session: AsyncSession = Depends(get_session_dependency),
):
    result = await session.execute(select(Provider).where(Provider.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    await session.delete(provider)
    await session.flush()

    await audit_log(session, user.sub, "delete_provider", "provider", provider_id, {"name": provider.name})

    router = await get_router(session)
    await router.reload()


@router.get("/{provider_id}/health", response_model=ProviderHealthResponse)
async def get_provider_health(
    provider_id: str,
    user: dict = Depends(require_operator),
    session: AsyncSession = Depends(get_session_dependency),
):
    result = await session.execute(select(Provider).where(Provider.id == provider_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Provider not found")

    router = await get_router(session)
    health_results = await router.health_check_all()
    health = health_results.get(provider_id, {})

    return ProviderHealthResponse(
        provider_id=provider_id,
        healthy=health.get("healthy", False),
        latency_ms=health.get("latency_ms"),
        error=health.get("error"),
        circuit_open=health.get("circuit_open", False),
        consecutive_failures=health.get("consecutive_failures", 0),
    )


@router.post("/{provider_id}/test", response_model=ProviderTestResponse)
async def test_provider(
    provider_id: str,
    user: dict = Depends(require_operator),
    session: AsyncSession = Depends(get_session_dependency),
):
    result = await session.execute(select(Provider).where(Provider.id == provider_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Provider not found")

    router = await get_router(session)
    result = await router.test_provider(provider_id)

    return ProviderTestResponse(**result)