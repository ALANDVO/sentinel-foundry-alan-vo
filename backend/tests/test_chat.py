import pytest
from httpx import AsyncClient


class TestChatAPI:
    @pytest.mark.asyncio
    async def test_anthropic_messages_anonymous_allowed(self, client: AsyncClient):
        response = await client.post("/v1/messages", json={
            "model": "claude-3-sonnet",
            "messages": [{"role": "user", "content": "Hello"}],
        })
        assert response.status_code in (503, 500)

    @pytest.mark.asyncio
    async def test_openai_chat_anonymous_allowed(self, client: AsyncClient):
        response = await client.post("/v1/chat/completions", json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello"}],
        })
        assert response.status_code in (503, 500)

    @pytest.mark.asyncio
    async def test_anthropic_messages_with_demo(self, client: AsyncClient):
        await client.post("/auth/demo-login")
        response = await client.post("/v1/messages", json={
            "model": "claude-3-sonnet",
            "messages": [{"role": "user", "content": "Hello"}],
        })
        assert response.status_code in (503, 500)

    @pytest.mark.asyncio
    async def test_openai_chat_with_demo(self, client: AsyncClient):
        await client.post("/auth/demo-login")
        response = await client.post("/v1/chat/completions", json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello"}],
        })
        assert response.status_code in (503, 500)

    @pytest.mark.asyncio
    async def test_chat_validation(self, client: AsyncClient):
        await client.post("/auth/demo-login")
        response = await client.post("/v1/messages", json={})
        assert response.status_code == 422

        response = await client.post("/v1/chat/completions", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_streaming_endpoint_exists(self, client: AsyncClient):
        await client.post("/auth/demo-login")
        response = await client.post("/v1/messages", json={
            "model": "claude-3-sonnet",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": True,
        })
        assert response.status_code not in (401, 404, 422)

        response = await client.post("/v1/chat/completions", json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": True,
        })
        assert response.status_code not in (401, 404, 422)