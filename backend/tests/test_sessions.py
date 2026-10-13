import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Session, Message


class TestSessionsAPI:
    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, client: AsyncClient):
        response = await client.get("/api/v1/sessions")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_session_crud_with_demo(self, client: AsyncClient, sample_session_data):
        await client.post("/auth/demo-login")

        # Create session
        create_resp = await client.post("/api/v1/sessions", json=sample_session_data)
        assert create_resp.status_code == 201
        session = create_resp.json()
        assert session["title"] == sample_session_data["title"]
        assert "id" in session
        session_id = session["id"]

        # List sessions
        list_resp = await client.get("/api/v1/sessions")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total"] == 1

        # Get session
        get_resp = await client.get(f"/api/v1/sessions/{session_id}")
        assert get_resp.status_code == 200
        session_data = get_resp.json()
        assert session_data["id"] == session_id
        assert "messages" in session_data

        # Update session
        update_resp = await client.patch(f"/api/v1/sessions/{session_id}", json={"title": "Updated Title"})
        assert update_resp.status_code == 200
        assert update_resp.json()["title"] == "Updated Title"

        # Delete session
        delete_resp = await client.delete(f"/api/v1/sessions/{session_id}")
        assert delete_resp.status_code == 204

        # Verify deleted
        list_resp = await client.get("/api/v1/sessions")
        assert list_resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_add_message_to_session(self, client: AsyncClient, sample_session_data):
        await client.post("/auth/demo-login")
        create_resp = await client.post("/api/v1/sessions", json=sample_session_data)
        session_id = create_resp.json()["id"]

        # Add user message
        msg_resp = await client.post(f"/api/v1/sessions/{session_id}/messages", json={
            "role": "user",
            "content": "Hello, world!",
        })
        assert msg_resp.status_code == 201
        message = msg_resp.json()
        assert message["role"] == "user"
        assert message["content"] == "Hello, world!"

        # Add assistant message
        msg_resp = await client.post(f"/api/v1/sessions/{session_id}/messages", json={
            "role": "assistant",
            "content": "Hi there!",
        })
        assert msg_resp.status_code == 201

        # Verify messages in session
        get_resp = await client.get(f"/api/v1/sessions/{session_id}")
        session = get_resp.json()
        assert len(session["messages"]) == 2
        assert session["message_count"] == 2

    @pytest.mark.asyncio
    async def test_export_session(self, client: AsyncClient, sample_session_data):
        await client.post("/auth/demo-login")
        create_resp = await client.post("/api/v1/sessions", json=sample_session_data)
        session_id = create_resp.json()["id"]

        # Add a message
        await client.post(f"/api/v1/sessions/{session_id}/messages", json={
            "role": "user",
            "content": "Test message",
        })

        export_resp = await client.get(f"/api/v1/sessions/{session_id}/export")
        assert export_resp.status_code == 200
        assert export_resp.headers["content-type"] == "application/json"
        assert f"session-{session_id}.json" in export_resp.headers.get("content-disposition", "")

        data = export_resp.json()
        assert data["session"]["id"] == session_id
        assert len(data["messages"]) == 1

    @pytest.mark.asyncio
    async def test_session_pagination(self, client: AsyncClient):
        await client.post("/auth/demo-login")
        for i in range(10):
            await client.post("/api/v1/sessions", json={"title": f"Session {i}"})

        page1 = await client.get("/api/v1/sessions?page=1&page_size=3")
        assert page1.status_code == 200
        data = page1.json()
        assert len(data["items"]) == 3
        assert data["page"] == 1
        assert data["total"] == 10

    @pytest.mark.asyncio
    async def test_session_validation(self, client: AsyncClient):
        await client.post("/auth/demo-login")
        # Missing required fields - should work since all are optional
        resp = await client.post("/api/v1/sessions", json={})
        assert resp.status_code == 201

        # Invalid role in message
        create_resp = await client.post("/api/v1/sessions", json={"title": "Test"})
        session_id = create_resp.json()["id"]
        msg_resp = await client.post(f"/api/v1/sessions/{session_id}/messages", json={
            "role": "invalid",
            "content": "Test",
        })
        assert msg_resp.status_code == 422