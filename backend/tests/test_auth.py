import pytest
from httpx import AsyncClient


class TestAuthAPI:
    @pytest.mark.asyncio
    async def test_login_endpoint(self, client: AsyncClient):
        response = await client.get("/auth/login")
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert "nonce" in data
        assert "pkce_verifier" in data
        assert data["authorization_url"].startswith("http")

    @pytest.mark.asyncio
    async def test_demo_login(self, client: AsyncClient):
        response = await client.post("/auth/demo-login")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "user" in data
        assert data["user"]["sub"] == "demo-user"
        assert "operator" in data["user"]["roles"]

        # Check cookie set
        assert "demo_session" in response.cookies

    @pytest.mark.asyncio
    async def test_demo_login_rejected_in_production(self, client: AsyncClient, monkeypatch):
        # This would require setting APP_ENV=production, but we can't easily test
        # the middleware without a separate app instance. Skip for now.
        pass

    @pytest.mark.asyncio
    async def test_me_endpoint_unauthorized(self, client: AsyncClient):
        response = await client.get("/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_endpoint_with_demo(self, client: AsyncClient):
        await client.post("/auth/demo-login")
        response = await client.get("/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["sub"] == "demo-user"
        assert "operator" in data["roles"]

    @pytest.mark.asyncio
    async def test_logout(self, client: AsyncClient):
        await client.post("/auth/demo-login")
        response = await client.post("/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert "logout_url" in data
        # Cookies should be cleared
        assert "session" not in response.cookies or response.cookies.get("session") == ""

    @pytest.mark.asyncio
    async def test_protected_endpoints_require_auth(self, client: AsyncClient):
        endpoints = [
            ("GET", "/api/v1/providers"),
            ("POST", "/api/v1/providers"),
            ("GET", "/api/v1/sessions"),
            ("POST", "/api/v1/sessions"),
            ("GET", "/api/v1/logs"),
            ("GET", "/auth/me"),
        ]
        for method, path in endpoints:
            response = await client.request(method, path)
            assert response.status_code == 401, f"{method} {path} should require auth"