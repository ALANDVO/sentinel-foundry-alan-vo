from typing import Optional, List, Dict, Any, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
import asyncio
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.models import Provider, ProviderHealth, RequestLog, Session, Message
from app.services.providers import (
    BaseProvider,
    ProviderConfig,
    ChatRequest,
    ChatResponse,
    StreamChunk,
    ProviderError,
    create_provider,
)

logger = logging.getLogger(__name__)


@dataclass
class CircuitBreakerState:
    failures: int = 0
    last_failure: Optional[datetime] = None
    open: bool = False
    opened_at: Optional[datetime] = None

    def record_success(self):
        self.failures = 0
        self.open = False
        self.opened_at = None

    def record_failure(self, threshold: int = 5, timeout_seconds: int = 30) -> bool:
        self.failures += 1
        self.last_failure = datetime.now(timezone.utc)
        if self.failures >= threshold and not self.open:
            self.open = True
            self.opened_at = datetime.now(timezone.utc)
            return True
        return False

    def can_attempt(self, timeout_seconds: int = 30) -> bool:
        if not self.open:
            return True
        if self.opened_at:
            elapsed = (datetime.now(timezone.utc) - self.opened_at).total_seconds()
            if elapsed >= timeout_seconds:
                return True
        return False


class ProviderRouter:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._providers: Dict[str, BaseProvider] = {}
        self._circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self._lock = asyncio.Lock()

    async def initialize(self):
        await self._load_providers()

    async def _load_providers(self):
        result = await self.session.execute(
            select(Provider).where(Provider.enabled == True).order_by(desc(Provider.priority))
        )
        providers = result.scalars().all()

        for p in providers:
            config = ProviderConfig(
                id=p.id,
                name=p.name,
                type=p.type,
                base_url=p.base_url,
                api_key=p.api_key,
                model=p.model,
                timeout_seconds=p.timeout_seconds,
                max_retries=p.max_retries,
                extra_config=p.extra_config,
            )
            self._providers[p.id] = create_provider(config)
            self._circuit_breakers[p.id] = CircuitBreakerState()

        logger.info(f"Loaded {len(self._providers)} providers")

    async def reload(self):
        async with self._lock:
            for provider in self._providers.values():
                await provider.close()
            self._providers.clear()
            self._circuit_breakers.clear()
            await self._load_providers()

    def get_provider(self, provider_id: str) -> Optional[BaseProvider]:
        return self._providers.get(provider_id)

    def get_all_providers(self) -> List[BaseProvider]:
        return list(self._providers.values())

    def get_provider_ids(self) -> List[str]:
        return list(self._providers.keys())

    def is_healthy(self, provider_id: str) -> bool:
        cb = self._circuit_breakers.get(provider_id)
        if not cb:
            return False
        return not cb.open or cb.can_attempt()

    def get_circuit_state(self, provider_id: str) -> Optional[CircuitBreakerState]:
        return self._circuit_breakers.get(provider_id)

    async def chat(
        self,
        request: ChatRequest,
        preferred_provider_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> ChatResponse:
        provider_ids = self._get_provider_order(preferred_provider_id)

        last_error = None
        for provider_id in provider_ids:
            if not self.is_healthy(provider_id):
                logger.debug(f"Skipping unhealthy provider: {provider_id}")
                continue

            provider = self._providers[provider_id]
            cb = self._circuit_breakers[provider_id]

            try:
                response = await provider.chat(request)
                cb.record_success()
                await self._log_request(provider_id, session_id, request, response, None)
                return response
            except Exception as e:
                last_error = e
                cb.record_failure()
                await self._log_request(provider_id, session_id, request, None, e)
                logger.warning(f"Provider {provider_id} failed: {e}")
                await self._update_health(provider_id, False, str(e))

        raise ProviderError(
            f"All providers failed. Last error: {last_error}",
            status_code=503,
            provider="",
            retryable=True,
        )

    async def stream_chat(
        self,
        request: ChatRequest,
        preferred_provider_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AsyncIterator[StreamChunk]:
        provider_ids = self._get_provider_order(preferred_provider_id)

        last_error = None
        for provider_id in provider_ids:
            if not self.is_healthy(provider_id):
                logger.debug(f"Skipping unhealthy provider: {provider_id}")
                continue

            provider = self._providers[provider_id]
            cb = self._circuit_breakers[provider_id]

            try:
                async for chunk in provider.stream_chat(request):
                    yield chunk
                cb.record_success()
                return
            except Exception as e:
                last_error = e
                cb.record_failure()
                logger.warning(f"Provider {provider_id} stream failed: {e}")
                await self._update_health(provider_id, False, str(e))

        raise ProviderError(
            f"All providers failed for streaming. Last error: {last_error}",
            status_code=503,
            provider="",
            retryable=True,
        )

    def _get_provider_order(self, preferred_provider_id: Optional[str] = None) -> List[str]:
        ids = list(self._providers.keys())
        if preferred_provider_id and preferred_provider_id in ids:
            ids.remove(preferred_provider_id)
            ids.insert(0, preferred_provider_id)
        return ids

    async def _log_request(
        self,
        provider_id: str,
        session_id: Optional[str],
        request: ChatRequest,
        response: Optional[ChatResponse],
        error: Optional[Exception],
    ):
        log = RequestLog(
            provider_id=provider_id,
            session_id=session_id,
            method="POST",
            path="/v1/chat/completions",
            request_body=request.model_dump(exclude_none=True),
            response_status=200 if response else 500,
            response_body=response.model_dump(exclude_none=True) if response else None,
            error_message=str(error) if error else None,
        )
        self.session.add(log)
        await self.session.flush()

    async def _update_health(self, provider_id: str, healthy: bool, error: Optional[str] = None):
        from app.services.providers import BaseProvider
        provider = self._providers.get(provider_id)
        latency = None
        if provider:
            try:
                healthy, latency, error = await provider.health_check()
            except Exception as e:
                healthy, latency, error = False, None, str(e)

        health = ProviderHealth(
            provider_id=provider_id,
            healthy=healthy,
            latency_ms=latency,
            error_message=error,
            consecutive_failures=self._circuit_breakers[provider_id].failures,
            circuit_open=self._circuit_breakers[provider_id].open,
            circuit_open_at=self._circuit_breakers[provider_id].opened_at,
        )
        self.session.add(health)
        await self.session.flush()

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        results = {}
        for provider_id, provider in self._providers.items():
            healthy, latency, error = await provider.health_check()
            cb = self._circuit_breakers.get(provider_id)

            await self._update_health(provider_id, healthy, error)

            results[provider_id] = {
                "healthy": healthy,
                "latency_ms": latency,
                "error": error,
                "circuit_open": cb.open if cb else False,
                "consecutive_failures": cb.failures if cb else 0,
            }
        return results

    async def test_provider(self, provider_id: str) -> Dict[str, Any]:
        provider = self._providers.get(provider_id)
        if not provider:
            return {"success": False, "error": "Provider not found"}

        try:
            healthy, latency, error = await provider.health_check()
            models = await provider.list_models() if healthy else []
            return {
                "success": healthy,
                "latency_ms": latency,
                "error": error,
                "models": models,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def close(self):
        for provider in self._providers.values():
            await provider.close()


async def get_router(session: AsyncSession) -> ProviderRouter:
    router = ProviderRouter(session)
    await router.initialize()
    return router