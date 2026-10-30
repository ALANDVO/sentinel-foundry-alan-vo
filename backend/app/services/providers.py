from typing import Optional, List, Dict, Any, AsyncIterator
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import httpx
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProviderConfig:
    id: str
    name: str
    type: str
    base_url: str
    api_key: Optional[str] = None
    model: Optional[str] = None
    timeout_seconds: int = 30
    max_retries: int = 3
    extra_config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ChatMessage:
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

@dataclass
class ChatRequest:
    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = None
    stream: bool = False
    extra_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ChatResponse:
    id: str
    model: str
    content: str
    role: str = "assistant"
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None

@dataclass
class StreamChunk:
    id: str
    model: str
    delta: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None

class ProviderError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        provider: str = "",
        retryable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.provider = provider
        self.retryable = retryable

class BaseProvider(ABC):
    def __init__(self, config: ProviderConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    @abstractmethod
    def _get_headers(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def _get_endpoint(self) -> str:
        pass

    @abstractmethod
    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def _build_payload(self, request: ChatRequest) -> Dict[str, Any]:
        pass

    @abstractmethod
    def _parse_response(self, data: Dict[str, Any]) -> ChatResponse:
        pass

    @abstractmethod
    def _parse_stream_chunk(self, line: str) -> Optional[StreamChunk]:
        pass

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout_seconds),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._client

    async def chat(self, request: ChatRequest) -> ChatResponse:
        client = self._get_client()
        headers = self._get_headers()
        payload = self._build_payload(request)
        endpoint = self._get_endpoint()

        for attempt in range(self.config.max_retries + 1):
            try:
                response = await client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return self._parse_response(data)
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self.config.max_retries:
                    logger.warning(
                        f"Provider {self.config.id} returned {e.response.status_code}, retrying..."
                    )
                    continue
                raise ProviderError(
                    f"HTTP error: {e.response.status_code} - {e.response.text}",
                    status_code=e.response.status_code,
                    provider=self.config.id,
                    retryable=e.response.status_code >= 500,
                )
            except httpx.RequestError as e:
                if attempt < self.config.max_retries:
                    logger.warning(f"Provider {self.config.id} request failed, retrying: {e}")
                    continue
                raise ProviderError(
                    f"Request failed: {e}",
                    status_code=503,
                    provider=self.config.id,
                    retryable=True,
                )

        raise ProviderError(
            "Max retries exceeded",
            status_code=503,
            provider=self.config.id,
            retryable=True,
        )

    async def stream_chat(self, request: ChatRequest) -> AsyncIterator[StreamChunk]:
        client = self._get_client()
        headers = self._get_headers()
        payload = self._build_payload(request)
        payload["stream"] = True
        endpoint = self._get_endpoint()

        async with client.stream("POST", endpoint, headers=headers, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    line = line[6:]
                if line.strip() == "[DONE]":
                    break
                if line.strip():
                    chunk = self._parse_stream_chunk(line)
                    if chunk:
                        yield chunk

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

class OpenAICompatibleProvider(BaseProvider):
    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _get_endpoint(self) -> str:
        base = self.config.base_url.rstrip("/")
        return f"{base}/chat/completions"

    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        converted = []
        for msg in messages:
            converted_msg = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                converted_msg["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                converted_msg["tool_call_id"] = msg.tool_call_id
            if msg.name:
                converted_msg["name"] = msg.name
            converted.append(converted_msg)
        return converted

    def _build_payload(self, request: ChatRequest) -> Dict[str, Any]:
        model = request.model or self.config.model
        messages = self._convert_messages(request.messages)

        payload = {
            "model": model,
            "messages": messages,
        }

        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.tools is not None:
            payload["tools"] = request.tools
        if request.tool_choice is not None:
            payload["tool_choice"] = request.tool_choice

        return payload

    def _parse_response(self, data: Dict[str, Any]) -> ChatResponse:
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = data.get("usage")

        return ChatResponse(
            id=data.get("id", ""),
            model=data.get("model", ""),
            content=message.get("content", ""),
            role=message.get("role", "assistant"),
            finish_reason=choice.get("finish_reason"),
            usage=usage,
            tool_calls=message.get("tool_calls"),
        )

    def _parse_stream_chunk(self, line: str) -> Optional[StreamChunk]:
        try:
            data = json.loads(line)
            choice = data.get("choices", [{}])[0]
            delta = choice.get("delta", {})
            finish_reason = choice.get("finish_reason")

            if not delta and finish_reason is None:
                return None

            return StreamChunk(
                id=data.get("id", ""),
                model=data.get("model", ""),
                delta=delta if delta else None,
                finish_reason=finish_reason,
                usage=data.get("usage"),
            )
        except json.JSONDecodeError:
            return None

class AnthropicProvider(BaseProvider):
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key or "",
            "anthropic-version": "2023-06-01",
        }

    def _get_endpoint(self) -> str:
        base = self.config.base_url.rstrip("/")
        return f"{base}/v1/messages"

    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        converted = []
        system_prompt = None

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                converted.append({"role": msg.role, "content": msg.content})

        if system_prompt:
            converted.insert(0, {"role": "system", "content": system_prompt})

        return converted

    def _build_payload(self, request: ChatRequest) -> Dict[str, Any]:
        model = request.model or self.config.model
        messages = self._convert_messages(request.messages)

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,
        }

        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.tools is not None:
            payload["tools"] = request.tools
        if request.tool_choice is not None:
            payload["tool_choice"] = request.tool_choice

        return payload

    def _parse_response(self, data: Dict[str, Any]) -> ChatResponse:
        content = ""
        tool_calls = None

        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")
            elif block.get("type") == "tool_use":
                if tool_calls is None:
                    tool_calls = []
                tool_calls.append(
                    {
                        "id": block.get("id"),
                        "type": "function",
                        "function": {
                            "name": block.get("name"),
                            "arguments": json.dumps(block.get("input", {})),
                        },
                    }
                )

        usage = data.get("usage")
        if usage:
            usage = {
                "prompt_tokens": usage.get("input_tokens", 0),
                "completion_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            }

        return ChatResponse(
            id=data.get("id", ""),
            model=data.get("model", ""),
            content=content,
            role="assistant",
            finish_reason=data.get("stop_reason"),
            usage=usage,
            tool_calls=tool_calls,
        )

    def _parse_stream_chunk(self, line: str) -> Optional[StreamChunk]:
        try:
            data = json.loads(line)
            event_type = data.get("type")

            if event_type == "content_block_delta":
                delta = data.get("delta", {})
                if delta.get("type") == "text_delta":
                    return StreamChunk(
                        id=data.get("id", ""),
                        model=data.get("model", ""),
                        delta={"content": delta.get("text", "")},
                    )
            elif event_type == "message_delta":
                delta = data.get("delta", {})
                return StreamChunk(
                    id=data.get("id", ""),
                    model=data.get("model", ""),
                    delta={"content": ""},
                    finish_reason=delta.get("stop_reason"),
                    usage=data.get("usage"),
                )
            elif event_type == "message_start":
                return StreamChunk(
                    id=data.get("message", {}).get("id", ""),
                    model=data.get("message", {}).get("model", ""),
                    delta={"role": "assistant"},
                )

            return None
        except json.JSONDecodeError:
            return None

class GeminiProvider(BaseProvider):
    def _get_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}

    def _get_endpoint(self) -> str:
        base = self.config.base_url.rstrip("/")
        model = self.config.model or "gemini-pro"
        api_key = self.config.api_key
        if api_key:
            return f"{base}/v1beta/models/{model}:generateContent?key={api_key}"
        return f"{base}/v1beta/models/{model}:generateContent"

    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        converted = []
        for msg in messages:
            role = "user" if msg.role == "user" else "model"
            converted.append({"role": role, "parts": [{"text": msg.content}]})
        return converted

    def _build_payload(self, request: ChatRequest) -> Dict[str, Any]:
        messages = self._convert_messages(request.messages)

        payload = {"contents": messages}

        generation_config = {}
        if request.temperature is not None:
            generation_config["temperature"] = request.temperature
        if request.max_tokens is not None:
            generation_config["maxOutputTokens"] = request.max_tokens
        if generation_config:
            payload["generationConfig"] = generation_config

        if request.tools is not None:
            payload["tools"] = [{"functionDeclarations": request.tools}]

        return payload

    def _parse_response(self, data: Dict[str, Any]) -> ChatResponse:
        candidate = data.get("candidates", [{}])[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [{}])
        text = parts[0].get("text", "") if parts else ""

        usage = data.get("usageMetadata")
        if usage:
            usage = {
                "prompt_tokens": usage.get("promptTokenCount", 0),
                "completion_tokens": usage.get("candidatesTokenCount", 0),
                "total_tokens": usage.get("totalTokenCount", 0),
            }

        return ChatResponse(
            id=data.get("id", ""),
            model=data.get("modelVersion", ""),
            content=text,
            role="model",
            finish_reason=candidate.get("finishReason"),
            usage=usage,
        )

    def _parse_stream_chunk(self, line: str) -> Optional[StreamChunk]:
        try:
            data = json.loads(line)
            candidate = data.get("candidates", [{}])[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [{}])
            text = parts[0].get("text", "") if parts else ""

            return StreamChunk(
                id=data.get("id", ""),
                model=data.get("modelVersion", ""),
                delta={"content": text},
                finish_reason=candidate.get("finishReason"),
                usage=data.get("usageMetadata"),
            )
        except json.JSONDecodeError:
            return None

class OllamaProvider(BaseProvider):
    def _get_headers(self) -> Dict[str, str]:
        return {"Content-Type": "application/json"}

    def _get_endpoint(self) -> str:
        base = self.config.base_url.rstrip("/")
        return f"{base}/api/chat"

    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        converted = []
        for msg in messages:
            converted.append({"role": msg.role, "content": msg.content})
        return converted

    def _build_payload(self, request: ChatRequest) -> Dict[str, Any]:
        model = request.model or self.config.model
        messages = self._convert_messages(request.messages)

        payload = {
            "model": model,
            "messages": messages,
            "stream": request.stream,
        }

        options = {}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.max_tokens is not None:
            options["num_predict"] = request.max_tokens
        if options:
            payload["options"] = options

        return payload

    def _parse_response(self, data: Dict[str, Any]) -> ChatResponse:
        message = data.get("message", {})

        return ChatResponse(
            id=data.get("id", ""),
            model=data.get("model", ""),
            content=message.get("content", ""),
            role=message.get("role", "assistant"),
            finish_reason=data.get("done_reason"),
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            },
        )

    def _parse_stream_chunk(self, line: str) -> Optional[StreamChunk]:
        try:
            data = json.loads(line)
            message = data.get("message", {})

            return StreamChunk(
                id="",
                model=data.get("model", ""),
                delta={"content": message.get("content", ""), "role": message.get("role", "assistant")},
                finish_reason=data.get("done_reason") if data.get("done") else None,
            )
        except json.JSONDecodeError:
            return None

def create_provider(config: ProviderConfig) -> BaseProvider:
    provider_type = config.type.lower()

    if provider_type == "openai-compatible":
        return OpenAICompatibleProvider(config)
    elif provider_type == "anthropic":
        return AnthropicProvider(config)
    elif provider_type == "gemini":
        return GeminiProvider(config)
    elif provider_type == "ollama":
        return OllamaProvider(config)
    else:
        raise ValueError(f"Unknown provider type: {config.type}")