from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta

from app.core.database import get_session_dependency
from app.core.auth import get_current_user, require_operator
from app.models import RequestLog, Provider

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])


class LogResponse(BaseModel):
    id: str
    provider_id: Optional[str]
    provider_name: Optional[str]
    session_id: Optional[str]
    method: str
    path: str
    request_body: Optional[dict]
    response_status: Optional[int]
    response_body: Optional[dict]
    latency_ms: Optional[int]
    error_message: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class LogStats(BaseModel):
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_latency_ms: float
    requests_by_provider: List[dict]
    requests_by_status: List[dict]
    error_rate: float


class PaginatedLogs(BaseModel):
    items: List[LogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("", response_model=PaginatedLogs)
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    provider_id: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    status_code: Optional[int] = Query(None),
    error_only: bool = Query(False),
    hours: int = Query(24, ge=1, le=168),
    user: dict = Depends(require_operator),
    session: AsyncSession = Depends(get_session_dependency),
):
    cutoff = datetime.now() - timedelta(hours=hours)

    query = select(RequestLog).where(RequestLog.created_at >= cutoff)

    if provider_id:
        query = query.where(RequestLog.provider_id == provider_id)
    if session_id:
        query = query.where(RequestLog.session_id == session_id)
    if status_code:
        query = query.where(RequestLog.response_status == status_code)
    if error_only:
        query = query.where(RequestLog.error_message.isnot(None))

    query = query.order_by(desc(RequestLog.created_at))

    total_result = await session.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    logs = result.scalars().all()

    provider_ids = [log.provider_id for log in logs if log.provider_id]
    provider_names = {}
    if provider_ids:
        prov_result = await session.execute(select(Provider).where(Provider.id.in_(provider_ids)))
        for p in prov_result.scalars():
            provider_names[p.id] = p.name

    items = []
    for log in logs:
        items.append(LogResponse(
            id=log.id,
            provider_id=log.provider_id,
            provider_name=provider_names.get(log.provider_id),
            session_id=log.session_id,
            method=log.method,
            path=log.path,
            request_body=log.request_body,
            response_status=log.response_status,
            response_body=log.response_body,
            latency_ms=log.latency_ms,
            error_message=log.error_message,
            created_at=log.created_at.isoformat(),
        ))

    return PaginatedLogs(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/stats", response_model=LogStats)
async def get_log_stats(
    hours: int = Query(24, ge=1, le=168),
    user: dict = Depends(require_operator),
    session: AsyncSession = Depends(get_session_dependency),
):
    cutoff = datetime.now() - timedelta(hours=hours)

    total_result = await session.execute(
        select(func.count(RequestLog.id)).where(RequestLog.created_at >= cutoff)
    )
    total = total_result.scalar() or 0

    success_result = await session.execute(
        select(func.count(RequestLog.id)).where(
            and_(RequestLog.created_at >= cutoff, RequestLog.response_status == 200)
        )
    )
    successful = success_result.scalar() or 0

    failed = total - successful

    avg_latency_result = await session.execute(
        select(func.avg(RequestLog.latency_ms)).where(
            and_(RequestLog.created_at >= cutoff, RequestLog.latency_ms.isnot(None))
        )
    )
    avg_latency = avg_latency_result.scalar() or 0.0

    by_provider_result = await session.execute(
        select(
            RequestLog.provider_id,
            func.count(RequestLog.id).label("count"),
            func.avg(RequestLog.latency_ms).label("avg_latency"),
        )
        .where(RequestLog.created_at >= cutoff)
        .group_by(RequestLog.provider_id)
    )
    by_provider = [
        {
            "provider_id": row.provider_id,
            "count": row.count,
            "avg_latency_ms": float(row.avg_latency) if row.avg_latency else 0,
        }
        for row in by_provider_result
    ]

    by_status_result = await session.execute(
        select(
            RequestLog.response_status,
            func.count(RequestLog.id).label("count"),
        )
        .where(RequestLog.created_at >= cutoff)
        .group_by(RequestLog.response_status)
    )
    by_status = [
        {"status": row.response_status, "count": row.count}
        for row in by_status_result
    ]

    return LogStats(
        total_requests=total,
        successful_requests=successful,
        failed_requests=failed,
        avg_latency_ms=float(avg_latency),
        requests_by_provider=by_provider,
        requests_by_status=by_status,
        error_rate=failed / total if total > 0 else 0.0,
    )