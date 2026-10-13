import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "environment" in data
        assert "demo_mode" in data

    @pytest.mark.asyncio
    async def test_ready_endpoint(self, client: AsyncClient):
        response = await client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ready", "not_ready")
        assert "database" in data
        assert "providers_loaded" in data
        assert "providers_healthy" in data

    @pytest.mark.asyncio
    async def test_version_endpoint(self, client: AsyncClient):
        response = await client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0.0"
        assert data["name"] == "sentinel-foundry"