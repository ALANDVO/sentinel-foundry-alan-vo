from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from pydantic import BaseModel, Field
from typing import Optional, List
import json
import logging
from datetime import datetime

from app.core.database import get_session_dependency
from app.core.auth import get_current_user, require_operator, audit_log
from app.models import Session, Message

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])

logger = logging.getLogger(__name__)


class SessionCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    model: Optional[str] = Field(None, max_length=200)
    provider_id: Optional[str] = None
    session_metadata: Optional[dict] = Field(None, alias="metadata")


class SessionUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500)
    session_metadata: Optional[dict] = Field(None, alias="metadata")




class MessageCreate(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system|tool)$")
    content: str
    tool_calls: Optional[List[dict]] = None
    tool_call_id: Optional[str] = None
    metadata: Optional[dict] = None


class MessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    tool_calls: Optional[List[dict]]
    tool_call_id: Optional[str]
    metadata: Optional[dict]
    created_at: str

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    id: str
    title: Optional[str]
    user_id: str
    model: Optional[str]
    provider_id: Optional[str]
    session_metadata: Optional[dict] = Field(None, alias="metadata")
    created_at: str
    updated_at: str
    message_count: int = 0

    class Config:
        from_attributes = True


class SessionWithMessages(SessionResponse):
    messages: List[MessageResponse] = []


class PaginatedSessions(BaseModel):
    items: List[SessionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("", response_model=PaginatedSessions)
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_dependency),
):
    query = select(Session).where(Session.user_id == user.sub).order_by(desc(Session.updated_at))

    total_result = await session.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    sessions = result.scalars().all()

    items = []
    for s in sessions:
        msg_count_result = await session.execute(
            select(func.count(Message.id)).where(Message.session_id == s.id)
        )
        msg_count = msg_count_result.scalar() or 0

        items.append(SessionResponse(
            id=s.id,
            title=s.title,
            user_id=s.user_id,
            model=s.model,
            provider_id=s.provider_id,
            metadata=s.session_metadata,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
            message_count=msg_count,
        ))

    return PaginatedSessions(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: SessionCreate,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_dependency),
):
    new_session = Session(
        title=data.title,
        user_id=user.sub,
        model=data.model,
        provider_id=data.provider_id,
        session_metadata=data.session_metadata,
    )
    session.add(new_session)
    await session.flush()

    await audit_log(session, user.sub, "create_session", "session", new_session.id, data.model_dump())

    return SessionResponse(
        id=new_session.id,
        title=new_session.title,
        user_id=new_session.user_id,
        model=new_session.model,
        provider_id=new_session.provider_id,
        metadata=new_session.session_metadata,
        created_at=new_session.created_at.isoformat(),
        updated_at=new_session.updated_at.isoformat(),
        message_count=0,
    )


@router.get("/{session_id}", response_model=SessionWithMessages)
async def get_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_dependency),
):
    result = await session.execute(select(Session).where(Session.id == session_id, Session.user_id == user.sub))
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    msg_result = await session.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()

    return SessionWithMessages(
        id=sess.id,
        title=sess.title,
        user_id=sess.user_id,
        model=sess.model,
        provider_id=sess.provider_id,
        metadata=sess.session_metadata,
        created_at=sess.created_at.isoformat(),
        updated_at=sess.updated_at.isoformat(),
        message_count=len(messages),
        messages=[MessageResponse(
            id=m.id,
            session_id=m.session_id,
            role=m.role,
            content=m.content,
            tool_calls=m.tool_calls,
            tool_call_id=m.tool_call_id,
            metadata=m.message_metadata,
            created_at=m.created_at.isoformat(),
        ) for m in messages],
    )


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    data: SessionUpdate,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_dependency),
):
    result = await session.execute(select(Session).where(Session.id == session_id, Session.user_id == user.sub))
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(sess, key, value)

    await session.flush()
    await audit_log(session, user.sub, "update_session", "session", session_id, update_data)

    msg_count_result = await session.execute(
        select(func.count(Message.id)).where(Message.session_id == session_id)
    )
    msg_count = msg_count_result.scalar() or 0

    return SessionResponse(
        id=sess.id,
        title=sess.title,
        user_id=sess.user_id,
        model=sess.model,
        provider_id=sess.provider_id,
        metadata=sess.session_metadata,
        created_at=sess.created_at.isoformat(),
        updated_at=sess.updated_at.isoformat(),
        message_count=msg_count,
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_dependency),
):
    result = await session.execute(select(Session).where(Session.id == session_id, Session.user_id == user.sub))
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    await session.delete(sess)
    await session.flush()
    await audit_log(session, user.sub, "delete_session", "session", session_id, {"title": sess.title})


@router.post("/{session_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def add_message(
    session_id: str,
    data: MessageCreate,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_dependency),
):
    result = await session.execute(select(Session).where(Session.id == session_id, Session.user_id == user.sub))
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    message = Message(
        session_id=session_id,
        role=data.role,
        content=data.content,
        tool_calls=data.tool_calls,
        tool_call_id=data.tool_call_id,
        message_metadata=data.metadata,
    )
    session.add(message)
    await session.flush()

    return MessageResponse(
        id=message.id,
        session_id=message.session_id,
        role=message.role,
        content=message.content,
        tool_calls=message.tool_calls,
        tool_call_id=message.tool_call_id,
        metadata=message.message_metadata,
        created_at=message.created_at.isoformat(),
    )


@router.get("/{session_id}/export")
async def export_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session_dependency),
):
    result = await session.execute(select(Session).where(Session.id == session_id, Session.user_id == user.sub))
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    msg_result = await session.execute(
        select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()

    export_data = {
        "session": {
            "id": sess.id,
            "title": sess.title,
            "model": sess.model,
            "provider_id": sess.provider_id,
            "metadata": sess.session_metadata,
            "created_at": sess.created_at.isoformat(),
            "updated_at": sess.updated_at.isoformat(),
        },
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "tool_calls": m.tool_calls,
                "tool_call_id": m.tool_call_id,
                "metadata": m.message_metadata,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
        "exported_at": datetime.now().isoformat(),
    }

    return StreamingResponse(
        iter([json.dumps(export_data, indent=2)]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=session-{session_id}.json"},
    )