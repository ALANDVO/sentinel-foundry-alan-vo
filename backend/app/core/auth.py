from typing import Optional, List
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_dependency
from app.core.security import (
    verify_token,
    decode_session_token,
    TokenData,
    create_session_token,
)
from app.models import AuditLog
from app.core.config import settings

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session_dependency),
) -> TokenData:
    if settings.demo_mode and settings.app_env == "development":
        demo_token = request.cookies.get("demo_session")
        if demo_token:
            token_data = decode_session_token(demo_token)
            if token_data:
                return token_data

    if credentials:
        try:
            return await verify_token(credentials.credentials)
        except Exception:
            pass

    session_token = request.cookies.get("session")
    if session_token:
        token_data = decode_session_token(session_token)
        if token_data:
            return token_data

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: AsyncSession = Depends(get_session_dependency),
) -> Optional[TokenData]:
    try:
        return await get_current_user(request, credentials, session)
    except HTTPException:
        return None


def require_roles(*required_roles: str):
    async def role_checker(user: TokenData = Depends(get_current_user)) -> TokenData:
        user_roles = set(user.roles)
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(required_roles)}",
            )
        return user

    return role_checker


require_viewer = require_roles("viewer", "operator", "admin")
require_operator = require_roles("operator", "admin")
require_admin = require_roles("admin")


async def audit_log(
    session: AsyncSession,
    user_id: Optional[str],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    request: Optional[Request] = None,
) -> None:
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    session.add(log)
    await session.flush()


def set_session_cookie(response: Response, token: str, max_age: int = 1800) -> None:
    response.set_cookie(
        key="session",
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="strict",
        path="/",
    )


def set_demo_cookie(response: Response, token: str, max_age: int = 1800) -> None:
    response.set_cookie(
        key="demo_session",
        value=token,
        max_age=max_age,
        httponly=True,
        secure=False,
        samesite="strict",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key="session", path="/", secure=settings.app_env == "production", samesite="strict")
    response.delete_cookie(key="demo_session", path="/", secure=False, samesite="strict")