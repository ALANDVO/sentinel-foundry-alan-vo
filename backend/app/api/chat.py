from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, AsyncIterator
import json
import logging
import uuid

from app.core.database import get_session_dependency
from app.core.auth import get_current_user_optional, audit_log
from app.services import get_router, ChatRequest, ChatMessage, StreamChunk, ProviderError
from app.models import Session, Message, RequestLog

router = APIRouter(prefix="/v1", tags=["chat"])

logger = logging.getLogger(__name__)


class AnthropicMessage(BaseModel):
    role: str
    content: str | List[Dict[str, Any]]


class AnthropicRequest(BaseModel):
    model: str
    messages: List[AnthropicMessage]
    system: Optional[str] = None
    max_tokens: int = Field(4096, ge=1, le=100000)
    temperature: Optional[float] = Field(None, ge=0, le=2)
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class AnthropicResponse(BaseModel):
    id: str
    type: str = "message"
    role: str = "assistant"
    content: List[Dict[str, Any]]
    model: str
    stop_reason: Optional[str] = None
    stop_sequence: Optional[str] = None
    usage: Dict[str, int]


class OpenAIChatRequest(BaseModel):
    model: str
    messages: List[Dict[str, Any]]
    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_tokens: Optional[int] = Field(None, ge=1)
    stream: bool = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = None


def convert_anthropic_to_internal(req: AnthropicRequest) -> ChatRequest:
    messages = []
    if req.system:
        messages.append(ChatMessage(role="system", content=req.system))
    for msg in req.messages:
        if isinstance(msg.content, str):
            messages.append(ChatMessage(role=msg.role, content=msg.content))
        else:
            content_parts = []
            for part in msg.content:
                if part.get("type") == "text":
                    content_parts.append(part.get("text", ""))
            messages.append(ChatMessage(role=msg.role, content="\n".join(content_parts)))

    return ChatRequest(
        messages=messages,
        model=req.model,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        stream=req.stream,
        tools=req.tools,
        tool_choice=req.tool_choice.get("type") if req.tool_choice else None,
        metadata=req.metadata,
    )


def convert_openai_to_internal(req: OpenAIChatRequest) -> ChatRequest:
    messages = []
    for msg in req.messages:
        messages.append(ChatMessage(role=msg["role"], content=msg.get("content", "")))

    return ChatRequest(
        messages=messages,
        model=req.model,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        stream=req.stream,
        tools=req.tools,
        tool_choice=req.tool_choice,
    )


def convert_internal_to_anthropic(response: Any, model: str) -> AnthropicResponse:
    content = []
    if response.content:
        content.append({"type": "text", "text": response.content})
    if response.tool_calls:
        for tc in response.tool_calls:
            content.append({
                "type": "tool_use",
                "id": tc.get("id", str(uuid.uuid4())),
                "name": tc.get("function", {}).get("name", ""),
                "input": tc.get("function", {}).get("arguments", {}),
            })

    return AnthropicResponse(
        id=response.id or str(uuid.uuid4()),
        role=response.role,
        content=content,
        model=model,
        stop_reason=response.finish_reason,
        usage=response.usage or {"input_tokens": 0, "output_tokens": 0},
    )


def format_sse_chunk(chunk: StreamChunk) -> str:
    data = {
        "type": "content_block_delta",
        "delta": chunk.delta,
    }
    if chunk.finish_reason:
        data = {
            "type": "message_delta",
            "delta": {"stop_reason": chunk.finish_reason},
        }
    return f"event: {data['type']}\ndata: {json.dumps(data)}\n\n"


async def get_session_id(request: Request, user_id: Optional[str]) -> Optional[str]:
    session_header = request.headers.get("x-session-id")
    if session_header:
        return session_header
    return None


@router.post("/messages")
async def anthropic_messages(
    request: Request,
    response: Response,
    data: AnthropicRequest,
    user: Optional[dict] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session_dependency),
):
    user_id = user.sub if user else "anonymous"
    internal_req = convert_anthropic_to_internal(data)
    session_id = await get_session_id(request, user_id)

    router = await get_router(session)

    if data.stream:
        async def stream_generator() -> AsyncIterator[bytes]:
            try:
                async for chunk in router.stream_chat(internal_req, session_id=session_id):
                    yield format_sse_chunk(chunk).encode()
                yield b"event: message_stop\ndata: {}\n\n"
            except ProviderError as e:
                error_data = {"type": "error", "error": {"message": str(e), "type": "provider_error"}}
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n".encode()
            except Exception as e:
                logger.error(f"Stream error: {e}")
                error_data = {"type": "error", "error": {"message": "Internal server error", "type": "internal_error"}}
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n".encode()

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        result = await router.chat(internal_req, session_id=session_id)
        anthropic_resp = convert_internal_to_anthropic(result, data.model)
        return anthropic_resp
    except ProviderError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/chat/completions")
async def openai_chat_completions(
    request: Request,
    response: Response,
    data: OpenAIChatRequest,
    user: Optional[dict] = Depends(get_current_user_optional),
    session: AsyncSession = Depends(get_session_dependency),
):
    user_id = user.sub if user else "anonymous"
    internal_req = convert_openai_to_internal(data)
    session_id = await get_session_id(request, user_id)

    router = await get_router(session)

    if data.stream:
        async def stream_generator() -> AsyncIterator[bytes]:
            try:
                async for chunk in router.stream_chat(internal_req, session_id=session_id):
                    chunk_data = {
                        "id": chunk.id,
                        "object": "chat.completion.chunk",
                        "model": chunk.model,
                        "choices": [{
                            "index": 0,
                            "delta": chunk.delta,
                            "finish_reason": chunk.finish_reason,
                        }],
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n".encode()
                yield b"data: [DONE]\n\n"
            except ProviderError as e:
                error_data = {"error": {"message": str(e), "type": "provider_error"}}
                yield f"data: {json.dumps(error_data)}\n\n".encode()
            except Exception as e:
                logger.error(f"Stream error: {e}")
                error_data = {"error": {"message": "Internal server error", "type": "internal_error"}}
                yield f"data: {json.dumps(error_data)}\n\n".encode()

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        result = await router.chat(internal_req, session_id=session_id)
        return {
            "id": result.id or str(uuid.uuid4()),
            "object": "chat.completion",
            "model": result.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": result.role,
                    "content": result.content,
                    "tool_calls": result.tool_calls,
                },
                "finish_reason": result.finish_reason,
            }],
            "usage": result.usage,
        }
    except ProviderError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")