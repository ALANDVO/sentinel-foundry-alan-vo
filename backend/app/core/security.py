from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
import secrets
import httpx
from pydantic import BaseModel

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    sub: str
    email: Optional[str] = None
    preferred_username: Optional[str] = None
    roles: list[str] = []
    exp: int
    iat: int
    nonce: Optional[str] = None


class OIDCConfig(BaseModel):
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    userinfo_endpoint: str
    end_session_endpoint: str


_oidc_config_cache: Optional[OIDCConfig] = None


async def get_oidc_config() -> OIDCConfig:
    global _oidc_config_cache
    if _oidc_config_cache:
        return _oidc_config_cache

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{settings.oidc_issuer_url}/.well-known/openid-configuration"
        )
        response.raise_for_status()
        data = response.json()
        _oidc_config_cache = OIDCConfig(**data)
        return _oidc_config_cache


async def get_jwks() -> Dict[str, Any]:
    oidc_config = await get_oidc_config()
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(oidc_config.jwks_uri)
        response.raise_for_status()
        return response.json()


async def verify_token(token: str) -> TokenData:
    oidc_config = await get_oidc_config()
    jwks = await get_jwks()

    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    if not kid:
        raise JWTError("Missing kid in token header")

    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if not key:
        raise JWTError(f"Key not found for kid: {kid}")

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)

    payload = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience=settings.keycloak_client_id,
        issuer=settings.oidc_issuer_url,
        options={"verify_exp": True, "verify_aud": True, "verify_iss": True},
    )

    return TokenData(**payload)


def create_state_token() -> str:
    return secrets.token_urlsafe(32)


def create_nonce() -> str:
    return secrets.token_urlsafe(32)


def create_pkce_verifier() -> str:
    return secrets.token_urlsafe(32)


def create_pkce_challenge(verifier: str) -> str:
    import hashlib
    import base64
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def build_authorization_url(state: str, nonce: str, pkce_challenge: str) -> str:
    oidc_config = OIDCConfig(
        issuer=settings.oidc_issuer_url,
        authorization_endpoint=f"{settings.oidc_issuer_url}/protocol/openid-connect/auth",
        token_endpoint=f"{settings.oidc_issuer_url}/protocol/openid-connect/token",
        jwks_uri=f"{settings.oidc_issuer_url}/protocol/openid-connect/certs",
        userinfo_endpoint=f"{settings.oidc_issuer_url}/protocol/openid-connect/userinfo",
        end_session_endpoint=f"{settings.oidc_issuer_url}/protocol/openid-connect/logout",
    )

    params = {
        "client_id": settings.keycloak_client_id,
        "response_type": "code",
        "scope": "openid email profile roles",
        "redirect_uri": settings.oidc_redirect_uri,
        "state": state,
        "nonce": nonce,
        "code_challenge": pkce_challenge,
        "code_challenge_method": "S256",
    }

    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{oidc_config.authorization_endpoint}?{query}"


async def exchange_code_for_tokens(code: str, pkce_verifier: str) -> Dict[str, Any]:
    oidc_config = await get_oidc_config()

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            oidc_config.token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.oidc_redirect_uri,
                "client_id": settings.keycloak_client_id,
                "client_secret": settings.keycloak_client_secret,
                "code_verifier": pkce_verifier,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()


async def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    oidc_config = await get_oidc_config()

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            oidc_config.token_endpoint,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": settings.keycloak_client_id,
                "client_secret": settings.keycloak_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()


async def logout_user(refresh_token: Optional[str] = None) -> None:
    oidc_config = await get_oidc_config()

    async with httpx.AsyncClient(timeout=10.0) as client:
        if refresh_token:
            await client.post(
                oidc_config.end_session_endpoint,
                data={
                    "client_id": settings.keycloak_client_id,
                    "client_secret": settings.keycloak_client_secret,
                    "refresh_token": refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_session_token(user_id: str, roles: list[str], expires_delta: timedelta = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=30)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload = {
        "sub": user_id,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "session",
    }

    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_session_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "session":
            return None
        return TokenData(**payload)
    except JWTError:
        return None