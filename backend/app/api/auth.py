from fastapi import APIRouter, Depends, Request, Response, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import logging

from app.core.database import get_session_dependency
from app.core.auth import (
    get_current_user,
    get_current_user_optional,
    require_admin,
    audit_log,
    set_session_cookie,
    clear_session_cookie,
    set_demo_cookie,
)
from app.core.security import (
    create_state_token,
    create_nonce,
    create_pkce_verifier,
    create_pkce_challenge,
    build_authorization_url,
    exchange_code_for_tokens,
    verify_token,
    create_session_token,
)
from app.core.config import settings
from app.models import AuditLog

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger(__name__)


class LoginResponse(BaseModel):
    authorization_url: str
    state: str
    nonce: str
    pkce_verifier: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class UserInfo(BaseModel):
    sub: str
    email: Optional[str] = None
    preferred_username: Optional[str] = None
    roles: list[str] = []


@router.get("/login", response_model=LoginResponse)
async def login(request: Request, response: Response):
    state = create_state_token()
    nonce = create_nonce()
    pkce_verifier = create_pkce_verifier()
    pkce_challenge = create_pkce_challenge(pkce_verifier)

    auth_url = build_authorization_url(state, nonce, pkce_challenge)

    response.set_cookie(
        key="oauth_state",
        value=state,
        max_age=600,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="oauth_nonce",
        value=nonce,
        max_age=600,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="oauth_pkce",
        value=pkce_verifier,
        max_age=600,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        path="/",
    )

    return LoginResponse(
        authorization_url=auth_url,
        state=state,
        nonce=nonce,
        pkce_verifier=pkce_verifier,
    )


@router.get("/callback")
async def callback(
    request: Request,
    response: Response,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session_dependency),
):
    if error:
        logger.error(f"OAuth error: {error} - {error_description}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {error_description or error}",
        )

    stored_state = request.cookies.get("oauth_state")
    stored_nonce = request.cookies.get("oauth_nonce")
    stored_pkce = request.cookies.get("oauth_pkce")

    if not stored_state or state != stored_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter",
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code",
        )

    try:
        tokens = await exchange_code_for_tokens(code, stored_pkce)
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code",
        )

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    id_token = tokens.get("id_token")

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No access token received",
        )

    try:
        token_data = await verify_token(access_token)
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    if stored_nonce and token_data.nonce != stored_nonce:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid nonce",
        )

    session_token = create_session_token(token_data.sub, token_data.roles)
    set_session_cookie(response, session_token)

    response.delete_cookie(key="oauth_state", path="/", secure=settings.app_env == "production", samesite="lax")
    response.delete_cookie(key="oauth_nonce", path="/", secure=settings.app_env == "production", samesite="lax")
    response.delete_cookie(key="oauth_pkce", path="/", secure=settings.app_env == "production", samesite="lax")

    await audit_log(
        session,
        token_data.sub,
        "login",
        "session",
        token_data.sub,
        {"method": "oidc"},
        request,
    )

    frontend_url = settings.oidc_redirect_uri.replace("/callback", "")
    return RedirectResponse(url=frontend_url, status_code=302)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_dependency),
):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        from app.core.security import logout_user
        try:
            await logout_user(refresh_token)
        except Exception:
            pass

    clear_session_cookie(response)

    await audit_log(
        session,
        user.sub,
        "logout",
        "session",
        user.sub,
        {},
        request,
    )

    logout_url = f"{settings.oidc_issuer_url}/protocol/openid-connect/logout"
    redirect_url = f"{logout_url}?post_logout_redirect_uri={settings.oidc_logout_redirect_uri}"

    return {"logout_url": redirect_url}


@router.get("/me", response_model=UserInfo)
async def me(user: dict = Depends(get_current_user)):
    return UserInfo(
        sub=user.sub,
        email=user.email,
        preferred_username=user.preferred_username,
        roles=user.roles,
    )


@router.post("/demo-login")
async def demo_login(response: Response, request: Request, session: AsyncSession = Depends(get_session_dependency)):
    if not settings.demo_mode or settings.app_env == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo mode not available in production",
        )

    demo_token = create_session_token("demo-user", ["operator"], timedelta(hours=24))
    set_demo_cookie(response, demo_token, max_age=86400)

    await audit_log(
        session,
        "demo-user",
        "demo_login",
        "session",
        "demo-user",
        {},
        request,
    )

    return {"message": "Demo login successful", "user": {"sub": "demo-user", "roles": ["operator"]}}


from datetime import timedelta