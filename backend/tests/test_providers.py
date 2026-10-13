import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Provider


class TestProvidersAPI:
    @pytest.mark.asyncio
    async def test_list_providers_empty(self, client: AsyncClient):
        response = await client.get("/api/v1/providers")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_provider_unauthorized(self, client: AsyncClient, sample_provider_data):
        response = await client.post("/api/v1/providers", json=sample_provider_data)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_provider_crud_with_demo_mode(self, client: AsyncClient, sample_provider_data, test_session: AsyncSession):
        # First demo login
        login_resp = await client.post("/auth/demo-login")
        assert login_resp.status_code == 200

        # Create provider
        create_resp = await client.post("/api/v1/providers", json=sample_provider_data)
        assert create_resp.status_code == 201
        provider = create_resp.json()
        assert provider["name"] == sample_provider_data["name"]
        assert provider["type"] == sample_provider_data["type"]
        assert "id" in provider
        provider_id = provider["id"]

        # List providers
        list_resp = await client.get("/api/v1/providers")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

        # Get provider
        get_resp = await client.get(f"/api/v1/providers/{provider_id}")
        assert get_resp.status_code == 200
        provider_data = get_resp.json()
        assert provider_data["id"] == provider_id

        # Update provider
        update_resp = await client.patch(f"/api/v1/providers/{provider_id}", json={"priority": 20, "model": "gpt-4"})
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["priority"] == 20
        assert updated["model"] == "gpt-4"

        # Delete provider
        delete_resp = await client.delete(f"/api/v1/providers/{provider_id}")
        assert delete_resp.status_code == 204

        # Verify deleted
        list_resp = await client.get("/api/v1/providers")
        assert list_resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_create_duplicate_provider_name(self, client: AsyncClient, sample_provider_data):
        await client.post("/auth/demo-login")
        await client.post("/api/v1/providers", json=sample_provider_data)
        resp = await client.post("/api/v1/providers", json=sample_provider_data)
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_provider_validation(self, client: AsyncClient):
        await client.post("/auth/demo-login")
        # Missing required fields
        resp = await client.post("/api/v1/providers", json={"name": "Test"})
        assert resp.status_code == 422

        # Invalid type
        resp = await client.post("/api/v1/providers", json={
            "name": "Test2",
            "type": "invalid",
            "base_url": "https://example.com",
        })
        assert resp.status_code == 422

        # Invalid URL
        resp = await client.post("/api/v1/providers", json={
            "name": "Test3",
            "type": "openai-compatible",
            "base_url": "not-a-url",
        })
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_provider_pagination(self, client: AsyncClient):
        await client.post("/auth/demo-login")
        for i in range(5):
            await client.post("/api/v1/providers", json={
                "name": f"Provider {i}",
                "type": "openai-compatible",
                "base_url": f"https://api{i}.example.com",
            })

        page1 = await client.get("/api/v1/providers?page=1&page_size=2")
        assert page1.status_code == 200
        data = page1.json()
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["total"] == 5
        assert data["total_pages"] == 3

    @pytest.mark.asyncio
    async def test_provider_filtering(self, client: AsyncClient):
        await client.post("/auth/demo-login")
        await client.post("/api/v1/providers", json={
            "name": "Enabled Provider",
            "type": "openai-compatible",
            "base_url": "https://api.example.com",
            "enabled": True,
        })
        await client.post("/api/v1/providers", json={
            "name": "Disabled Provider",
            "type": "openai-compatible",
            "base_url": "https://api2.example.com",
            "enabled": False,
        })

        enabled = await client.get("/api/v1/providers?enabled=true")
        assert enabled.status_code == 200
        assert enabled.json()["total"] == 1
        assert enabled.json()["items"][0]["name"] == "Enabled Provider"

        disabled = await client.get("/api/v1/providers?enabled=false")
        assert disabled.status_code == 200
        assert disabled.json()["total"] == 1
        assert disabled.json()["items"][0]["name"] == "Disabled Provider"