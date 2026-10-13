from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, AsyncIterator
from dataclasses import dataclass
from pydantic import BaseModel
import httpx
import json
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    id: str
    name: str
    type: str
    base_url: str
    api_key: Optional[str]
    model: Optional[str]
    timeout_seconds: int = 30
    max_retries: int = 2
    extra_config: Optional[Dict[str, Any]] = None


class ChatMessage(BaseModel):
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    id: str
    model: str
    role: str = "assistant"
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None


class StreamChunk(BaseModel):
    id: str
    model: str
    delta: Dict[str, Any]
    finish_reason: Optional[str] = None


class ProviderError(Exception):
    def __init__(self, message: str, status_code: int = 500, provider: str = "", retryable: bool = True):
        super().__init__(message)
        self.status_code = status_code
        self.provider = provider
        self.retryable = retryable


class BaseProvider(ABC):
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url.rstrip("/"),
            timeout=httpx.Timeout(config.timeout_seconds),
            headers=self._get_headers(),
        )

    @abstractmethod
    def _get_headers(self) -> Dict[str, str]:
        pass

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        pass

    @abstractmethod
    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        pass

    @abstractmethod
    async def health_check(self) -> tuple[bool, Optional[int], Optional[str]]:
        pass

    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        return [msg.model_dump(exclude_none=True) for msg in messages]

    async def close(self):
        await self.client.aclose()


class OpenAICompatibleProvider(BaseProvider):
    def _get_headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.config.api_key:
            h["Authorization"] = f"Bearer {self.config.api_key}"
        return h

    async def chat(self, request: ChatRequest) -> ChatResponse:
        payload = {k: v for k, v in {
            "model": request.model or self.config.model,
            "messages": self._convert_messages(request.messages),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
            "tools": request.tools,
            "tool_choice": request.tool_choice,
        }.items() if v is not None}
        resp = await self.client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        ch = data["choices"][0]
        return ChatResponse(
            id=data.get("id", ""), model=data.get("model", ""),
            role=ch["message"].get("role", "assistant"),
            content=ch["message"].get("content"),
            tool_calls=ch["message"].get("tool_calls"),
            finish_reason=ch.get("finish_reason"),
            usage=data.get("usage"),
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        payload = {k: v for k, v in {
            "model": request.model or self.config.model,
            "messages": self._convert_messages(request.messages),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
            "tools": request.tools,
            "tool_choice": request.tool_choice,
        }.items() if v is not None}
        async with self.client.stream("POST", "/chat/completions", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    d = line[6:]
                    if d.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(d)
                        ch = data["choices"][0]
                        yield StreamChunk(
                            id=data.get("id", ""), model=data.get("model", ""),
                            delta=ch.get("delta", {}), finish_reason=ch.get("finish_reason"),
                        )
                    except json.JSONDecodeError:
                        continue

    async def list_models(self) -> List[str]:
        resp = await self.client.get("/models")
        resp.raise_for_status()
        return [m["id"] for m in resp.json().get("data", [])]

    async def health_check(self) -> tuple[bool, Optional[int], Optional[str]]:
        t = time.perf_counter()
        try:
            resp = await self.client.get("/models")
            ms = int((time.perf_counter() - t) * 1000)
            return resp.status_code == 200, ms, None if resp.status_code == 200 else f"HTTP {resp.status_code}"
        except Exception as e:
            return False, int((time.perf_counter() - t) * 1000), str(e)


class AnthropicProvider(BaseProvider):
    def _get_headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json", "anthropic-version": "2023-06-01"}
        if self.config.api_key:
            h["x-api-key"] = self.config.api_key
        return h

    def _to_anthropic(self, messages: List[ChatMessage]) -> tuple[Optional[str], List[Dict[str, Any]]]:
        sys, conv = None, []
        for m in messages:
            if m.role == "system":
                sys = m.content
            else:
                conv.append({"role": m.role, "content": m.content})
        return sys, conv

    async def chat(self, request: ChatRequest) -> ChatResponse:
        sys, msgs = self._to_anthropic(request.messages)
        payload = {k: v for k, v in {
            "model": request.model or self.config.model,
            "messages": msgs, "max_tokens": request.max_tokens or 4096,
            "temperature": request.temperature, "stream": False,
            "tools": request.tools, "tool_choice": request.tool_choice,
            **({"system": sys} if sys else {}),
        }.items() if v is not None}
        resp = await self.client.post("/v1/messages", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return ChatResponse(
            id=data.get("id", ""), model=data.get("model", ""), role="assistant",
            content=data.get("content", [{}])[0].get("text") if data.get("content") else None,
            finish_reason=data.get("stop_reason"),
            usage={"input_tokens": data.get("usage", {}).get("input_tokens", 0),
                   "output_tokens": data.get("usage", {}).get("output_tokens", 0)},
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        sys, msgs = self._to_anthropic(request.messages)
        payload = {k: v for k, v in {
            "model": request.model or self.config.model,
            "messages": msgs, "max_tokens": request.max_tokens or 4096,
            "temperature": request.temperature, "stream": True,
            "tools": request.tools, "tool_choice": request.tool_choice,
            **({"system": sys} if sys else {}),
        }.items() if v is not None}
        async with self.client.stream("POST", "/v1/messages", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if data.get("type") == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield StreamChunk(
                                    id=data.get("message", {}).get("id", ""),
                                    model=self.config.model or "",
                                    delta={"content": delta.get("text", "")},
                                )
                        elif data.get("type") == "message_delta":
                            yield StreamChunk(
                                id=data.get("message", {}).get("id", ""),
                                model=self.config.model or "",
                                delta={}, finish_reason=data.get("delta", {}).get("stop_reason"),
                            )
                    except json.JSONDecodeError:
                        continue

    async def list_models(self) -> List[str]:
        resp = await self.client.get("/v1/models")
        resp.raise_for_status()
        return [m["id"] for m in resp.json().get("data", [])]

    async def health_check(self) -> tuple[bool, Optional[int], Optional[str]]:
        t = time.perf_counter()
        try:
            resp = await self.client.get("/v1/models")
            ms = int((time.perf_counter() - t) * 1000)
            return resp.status_code == 200, ms, None if resp.status_code == 200 else f"HTTP {resp.status_code}"
        except Exception as e:
            return False, int((time.perf_counter() - t) * 1000), str(e)


class GeminiProvider(BaseProvider):
    def _get_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}

    def _to_gemini(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        return [{"role": "user" if m.role in ("user", "system") else "model", "parts": [{"text": m.content}]} for m in messages]

    async def chat(self, request: ChatRequest) -> ChatResponse:
        model = request.model or self.config.model
        url = f"/v1beta/models/{model}:generateContent"
        if self.config.api_key:
            url += f"?key={self.config.api_key}"
        payload = {"contents": self._to_gemini(request.messages),
                   "generationConfig": {"temperature": request.temperature, "maxOutputTokens": request.max_tokens}}
        payload = {k: v for k, v in payload.items() if v is not None}
        resp = await self.client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        cand = data.get("candidates", [{}])[0]
        return ChatResponse(
            id="", model=model, role="assistant",
            content=cand.get("content", {}).get("parts", [{}])[0].get("text", ""),
            finish_reason=cand.get("finishReason"), usage=data.get("usageMetadata"),
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        model = request.model or self.config.model
        url = f"/v1beta/models/{model}:streamGenerateContent"
        if self.config.api_key:
            url += f"?key={self.config.api_key}&alt=sse"
        payload = {"contents": self._to_gemini(request.messages),
                   "generationConfig": {"temperature": request.temperature, "maxOutputTokens": request.max_tokens}}
        payload = {k: v for k, v in payload.items() if v is not None}
        async with self.client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        cand = data.get("candidates", [{}])[0]
                        txt = cand.get("content", {}).get("parts", [{}])[0].get("text", "")
                        if txt:
                            yield StreamChunk(id="", model=model, delta={"content": txt}, finish_reason=cand.get("finishReason"))
                    except json.JSONDecodeError:
                        continue

    async def list_models(self) -> List[str]:
        url = "/v1beta/models"
        if self.config.api_key:
            url += f"?key={self.config.api_key}"
        resp = await self.client.get(url)
        resp.raise_for_status()
        return [m["name"].split("/")[-1] for m in resp.json().get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]

    async def health_check(self) -> tuple[bool, Optional[int], Optional[str]]:
        t = time.perf_counter()
        try:
            await self.list_models()
            return True, int((time.perf_counter() - t) * 1000), None
        except Exception as e:
            return False, int((time.perf_counter() - t) * 1000), str(e)


class OllamaProvider(BaseProvider):
    def _get_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}

    async def chat(self, request: ChatRequest) -> ChatResponse:
        payload = {k: v for k, v in {
            "model": request.model or self.config.model,
            "messages": self._convert_messages(request.messages), "stream": False,
            "options": {"temperature": request.temperature, "num_predict": request.max_tokens},
        }.items() if v is not None}
        resp = await self.client.post("/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return ChatResponse(
            id="", model=request.model or self.config.model or "", role="assistant",
            content=data.get("message", {}).get("content", ""),
            finish_reason="stop" if data.get("done") else None,
            usage={"prompt_tokens": data.get("prompt_eval_count", 0), "completion_tokens": data.get("eval_count", 0)},
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        payload = {k: v for k, v in {
            "model": request.model or self.config.model,
            "messages": self._convert_messages(request.messages), "stream": True,
            "options": {"temperature": request.temperature, "num_predict": request.max_tokens},
        }.items() if v is not None}
        async with self.client.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                try:
                    data = json.loads(line)
                    c = data.get("message", {}).get("content", "")
                    if c:
                        yield StreamChunk(id="", model=request.model or self.config.model or "", delta={"content": c}, finish_reason="stop" if data.get("done") else None)
                except json.JSONDecodeError:
                    continue

    async def list_models(self) -> List[str]:
        resp = await self.client.get("/api/tags")
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]

    async def health_check(self) -> tuple[bool, Optional[int], Optional[str]]:
        t = time.perf_counter()
        try:
            resp = await self.client.get("/api/tags")
            ms = int((time.perf_counter() - t) * 1000)
            return resp.status_code == 200, ms, None if resp.status_code == 200 else f"HTTP {resp.status_code}"
        except Exception as e:
            return False, int((time.perf_counter() - t) * 1000), str(e)


def create_provider(config: ProviderConfig) -> BaseProvider:
    providers = {"openai-compatible": OpenAICompatibleProvider, "anthropic": AnthropicProvider,
                 "gemini": GeminiProvider, "ollama": OllamaProvider}
    cls = providers.get(config.type)
    if not cls:
        raise ValueError(f"Unknown provider type: {config.type}")
    return cls(config)