import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Provider, Session, Message, ProviderHealth, RequestLog, AuditLog
from datetime import datetime, timezone


class TestModels:
    @pytest.mark.asyncio
    async def test_create_provider(self, test_session: AsyncSession):
        provider = Provider(
            name="Test Provider",
            type="openai-compatible",
            base_url="https://api.example.com",
            api_key="sk-test",
            model="gpt-4o",
            enabled=True,
            priority=10,
        )
        test_session.add(provider)
        await test_session.flush()

        result = await test_session.execute(select(Provider).where(Provider.name == "Test Provider"))
        saved = result.scalar_one()
        assert saved.name == "Test Provider"
        assert saved.type == "openai-compatible"
        assert saved.enabled is True
        assert saved.priority == 10
        assert saved.created_at is not None

    @pytest.mark.asyncio
    async def test_provider_unique_name(self, test_session: AsyncSession):
        provider1 = Provider(name="Unique", type="openai-compatible", base_url="https://api1.com")
        provider2 = Provider(name="Unique", type="anthropic", base_url="https://api2.com")
        test_session.add_all([provider1, provider2])
        with pytest.raises(Exception):  # IntegrityError
            await test_session.flush()

    @pytest.mark.asyncio
    async def test_create_session(self, test_session: AsyncSession):
        session = Session(
            title="Test Session",
            user_id="user-123",
            model="gpt-4o",
            metadata={"key": "value"},
        )
        test_session.add(session)
        await test_session.flush()

        result = await test_session.execute(select(Session).where(Session.user_id == "user-123"))
        saved = result.scalar_one()
        assert saved.title == "Test Session"
        assert saved.user_id == "user-123"
        assert saved.metadata == {"key": "value"}

    @pytest.mark.asyncio
    async def test_create_message(self, test_session: AsyncSession):
        session = Session(user_id="user-123")
        test_session.add(session)
        await test_session.flush()

        message = Message(
            session_id=session.id,
            role="user",
            content="Hello world",
            metadata={"tokens": 100},
        )
        test_session.add(message)
        await test_session.flush()

        result = await test_session.execute(select(Message).where(Message.session_id == session.id))
        saved = result.scalar_one()
        assert saved.role == "user"
        assert saved.content == "Hello world"
        assert saved.metadata == {"tokens": 100}

    @pytest.mark.asyncio
    async def test_cascade_delete_session_messages(self, test_session: AsyncSession):
        session = Session(user_id="user-123")
        test_session.add(session)
        await test_session.flush()

        message = Message(session_id=session.id, role="user", content="Test")
        test_session.add(message)
        await test_session.flush()

        await test_session.delete(session)
        await test_session.flush()

        result = await test_session.execute(select(Message).where(Message.session_id == session.id))
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_provider_health(self, test_session: AsyncSession):
        provider = Provider(name="Health Test", type="openai-compatible", base_url="https://api.com")
        test_session.add(provider)
        await test_session.flush()

        health = ProviderHealth(
            provider_id=provider.id,
            healthy=True,
            latency_ms=150,
            error_message=None,
            consecutive_failures=0,
            circuit_open=False,
        )
        test_session.add(health)
        await test_session.flush()

        result = await test_session.execute(select(ProviderHealth).where(ProviderHealth.provider_id == provider.id))
        saved = result.scalar_one()
        assert saved.healthy is True
        assert saved.latency_ms == 150
        assert saved.circuit_open is False

    @pytest.mark.asyncio
    async def test_request_log(self, test_session: AsyncSession):
        provider = Provider(name="Log Test", type="openai-compatible", base_url="https://api.com")
        test_session.add(provider)
        await test_session.flush()

        log = RequestLog(
            provider_id=provider.id,
            session_id="session-123",
            method="POST",
            path="/v1/chat/completions",
            request_body={"model": "gpt-4o", "messages": []},
            response_status=200,
            response_body={"id": "resp-123", "choices": []},
            latency_ms=200,
            error_message=None,
        )
        test_session.add(log)
        await test_session.flush()

        result = await test_session.execute(select(RequestLog).where(RequestLog.provider_id == provider.id))
        saved = result.scalar_one()
        assert saved.method == "POST"
        assert saved.response_status == 200
        assert saved.latency_ms == 200

    @pytest.mark.asyncio
    async def test_audit_log(self, test_session: AsyncSession):
        log = AuditLog(
            user_id="user-123",
            action="create_provider",
            resource_type="provider",
            resource_id="provider-456",
            details={"name": "Test Provider"},
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )
        test_session.add(log)
        await test_session.flush()

        result = await test_session.execute(select(AuditLog).where(AuditLog.user_id == "user-123"))
        saved = result.scalar_one()
        assert saved.action == "create_provider"
        assert saved.resource_type == "provider"
        assert saved.details == {"name": "Test Provider"}