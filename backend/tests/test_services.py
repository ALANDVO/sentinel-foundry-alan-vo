import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.providers import (
    ProviderConfig,
    ChatRequest,
    ChatMessage,
    OpenAICompatibleProvider,
    AnthropicProvider,
    GeminiProvider,
    OllamaProvider,
    ProviderError,
)
from app.services.router import ProviderRouter, CircuitBreakerState
from app.models import Provider as ProviderModel


class TestProviderAdapters:
    @pytest.fixture
    def provider_config(self):
        return ProviderConfig(
            id="test-1",
            name="Test",
            type="openai-compatible",
            base_url="https://api.example.com",
            api_key="sk-test",
            model="gpt-4o",
        )

    @pytest.mark.asyncio
    async def test_openai_compatible_provider_headers(self, provider_config):
        provider = OpenAICompatibleProvider(provider_config)
        headers = provider._get_headers()
        assert headers["Authorization"] == "Bearer sk-test"
        assert headers["Content-Type"] == "application/json"
        await provider.close()

    @pytest.mark.asyncio
    async def test_anthropic_provider_headers(self, provider_config):
        provider_config.type = "anthropic"
        provider_config.api_key = "sk-ant-test"
        provider = AnthropicProvider(provider_config)
        headers = provider._get_headers()
        assert headers["x-api-key"] == "sk-ant-test"
        assert headers["anthropic-version"] == "2023-06-01"
        await provider.close()

    @pytest.mark.asyncio
    async def test_gemini_provider_headers(self, provider_config):
        provider_config.type = "gemini"
        provider_config.api_key = "gemini-key"
        provider = GeminiProvider(provider_config)
        headers = provider._get_headers()
        assert headers["Content-Type"] == "application/json"
        await provider.close()

    @pytest.mark.asyncio
    async def test_ollama_provider_headers(self, provider_config):
        provider_config.type = "ollama"
        provider_config.api_key = None
        provider = OllamaProvider(provider_config)
        headers = provider._get_headers()
        assert headers["Content-Type"] == "application/json"
        assert "Authorization" not in headers
        await provider.close()

    @pytest.mark.asyncio
    async def test_convert_messages(self, provider_config):
        provider = OpenAICompatibleProvider(provider_config)
        messages = [
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there"),
            ChatMessage(role="system", content="System prompt"),
        ]
        converted = provider._convert_messages(messages)
        assert len(converted) == 3
        assert converted[0]["role"] == "user"
        assert converted[0]["content"] == "Hello"
        await provider.close()


class TestCircuitBreaker:
    def test_circuit_breaker_initial_state(self):
        cb = CircuitBreakerState()
        assert cb.failures == 0
        assert cb.open is False
        assert cb.can_attempt() is True

    def test_circuit_breaker_opens_after_threshold(self):
        cb = CircuitBreakerState()
        for i in range(4):
            assert cb.record_failure(threshold=5) is False
            assert cb.open is False
        assert cb.record_failure(threshold=5) is True
        assert cb.open is True
        assert cb.can_attempt() is False

    def test_circuit_breaker_half_open_after_timeout(self):
        cb = CircuitBreakerState()
        for _ in range(5):
            cb.record_failure(threshold=5)
        assert cb.open is True
        # Simulate time passing
        import time
        from datetime import datetime, timezone
        cb.opened_at = datetime.fromtimestamp(time.time() - 31, tz=timezone.utc)
        assert cb.can_attempt(timeout_seconds=30) is True

    def test_circuit_breaker_resets_on_success(self):
        cb = CircuitBreakerState()
        for _ in range(5):
            cb.record_failure(threshold=5)
        assert cb.open is True
        cb.record_success()
        assert cb.open is False
        assert cb.failures == 0


class TestProviderRouter:
    @pytest.mark.asyncio
    async def test_router_initialization(self, test_session: AsyncSession):
        # Add test providers to DB
        provider1 = ProviderModel(
            name="Provider 1",
            type="openai-compatible",
            base_url="https://api1.com",
            enabled=True,
            priority=10,
        )
        provider2 = ProviderModel(
            name="Provider 2",
            type="openai-compatible",
            base_url="https://api2.com",
            enabled=True,
            priority=5,
        )
        test_session.add_all([provider1, provider2])
        await test_session.flush()

        with patch('app.services.providers.create_provider') as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.health_check.return_value = (True, 100, None)
            mock_create_provider.return_value = mock_provider

            router = ProviderRouter(test_session)
            await router.initialize()

            assert len(router._providers) == 2
            assert provider1.id in router._providers
            assert provider2.id in router._providers

    @pytest.mark.asyncio
    async def test_router_skips_disabled_providers(self, test_session: AsyncSession):
        provider1 = ProviderModel(name="Enabled", type="openai-compatible", base_url="https://api1.com", enabled=True)
        provider2 = ProviderModel(name="Disabled", type="openai-compatible", base_url="https://api2.com", enabled=False)
        test_session.add_all([provider1, provider2])
        await test_session.flush()

        with patch('app.services.providers.create_provider') as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.health_check.return_value = (True, 100, None)
            mock_create_provider.return_value = mock_provider

            router = ProviderRouter(test_session)
            await router.initialize()

            assert len(router._providers) == 1
            assert provider1.id in router._providers
            assert provider2.id not in router._providers

    @pytest.mark.asyncio
    async def test_router_priority_ordering(self, test_session: AsyncSession):
        provider1 = ProviderModel(name="Low", type="openai-compatible", base_url="https://api1.com", priority=1)
        provider2 = ProviderModel(name="High", type="openai-compatible", base_url="https://api2.com", priority=10)
        test_session.add_all([provider1, provider2])
        await test_session.flush()

        with patch('app.services.providers.create_provider') as mock_create_provider:
            mock_provider = AsyncMock()
            mock_provider.health_check.return_value = (True, 100, None)
            mock_create_provider.return_value = mock_provider

            router = ProviderRouter(test_session)
            await router.initialize()

            # High priority should come first
            ids = router.get_provider_ids()
            assert ids[0] == provider2.id
            assert ids[1] == provider1.id