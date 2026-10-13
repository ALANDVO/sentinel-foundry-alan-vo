import pytest
from httpx import AsyncClient


class TestLogsAPI:
    @pytest.mark.asyncio
    async def test_list_logs_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/v1/logs")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logs_with_demo(self, client: AsyncClient):
        await client.post("/auth/demo-login")
        response = await client.get("/api/v1/logs")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    @pytest.mark.asyncio
    async def test_log_stats(self, client: AsyncClient):
        await client.post("/auth/demo-login")
        response = await client.get("/api/v1/logs/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "successful_requests" in data
        assert "failed_requests" in data
        assert "avg_latency_ms" in data
        assert "requests_by_provider" in data
        assert "requests_by_status" in data
        assert "error_rate" in data

    @pytest.mark.asyncio
    async def test_log_filtering(self, client: AsyncClient):
        await client.post("/auth/demo-login")
        # Test various filters
        response = await client.get("/api/v1/logs?hours=1&error_only=true")
        assert response.status_code == 200

        response = await client.get("/api/v1/logs?status_code=200")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_log_pagination(self, client: AsyncClient):
        await client.post("/auth/demo-login")
        response = await client.get("/api/v1/logs?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10