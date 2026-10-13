from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Index,
    JSON,
    Float,
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone
import uuid


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Provider(Base):
    __tablename__ = "providers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    type = Column(String(50), nullable=False)  # openai-compatible, anthropic, gemini, ollama
    base_url = Column(String(500), nullable=False)
    api_key = Column(String(500), nullable=True)  # encrypted in production
    model = Column(String(200), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0, nullable=False)  # higher = preferred
    timeout_seconds = Column(Integer, default=30, nullable=False)
    max_retries = Column(Integer, default=2, nullable=False)
    extra_config = Column(JSON, nullable=True)  # provider-specific config
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    health_checks = relationship("ProviderHealth", back_populates="provider", cascade="all, delete-orphan")
    request_logs = relationship("RequestLog", back_populates="provider")

    __table_args__ = (
        Index("ix_providers_enabled_priority", "enabled", "priority"),
    )


class ProviderHealth(Base):
    __tablename__ = "provider_health"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_id = Column(String(36), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False)
    checked_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    healthy = Column(Boolean, nullable=False)
    latency_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    consecutive_failures = Column(Integer, default=0, nullable=False)
    circuit_open = Column(Boolean, default=False, nullable=False)
    circuit_open_at = Column(DateTime(timezone=True), nullable=True)

    provider = relationship("Provider", back_populates="health_checks")

    __table_args__ = (
        Index("ix_provider_health_provider_checked", "provider_id", "checked_at"),
    )


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_id = Column(String(36), ForeignKey("providers.id", ondelete="SET NULL"), nullable=True)
    session_id = Column(String(36), nullable=True)
    method = Column(String(10), nullable=False)
    path = Column(String(500), nullable=False)
    request_body = Column(JSON, nullable=True)
    response_status = Column(Integer, nullable=True)
    response_body = Column(JSON, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    provider = relationship("Provider", back_populates="request_logs")

    __table_args__ = (
        Index("ix_request_logs_created_at", "created_at"),
        Index("ix_request_logs_session_id", "session_id"),
        Index("ix_request_logs_provider_id", "provider_id"),
    )


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500), nullable=True)
    user_id = Column(String(100), nullable=False)
    model = Column(String(200), nullable=True)
    provider_id = Column(String(36), ForeignKey("providers.id", ondelete="SET NULL"), nullable=True)
    session_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_sessions_user_created", "user_id", "created_at"),
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False)
    tool_calls = Column(JSON, nullable=True)
    tool_call_id = Column(String(100), nullable=True)
    message_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    session = relationship("Session", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_session_created", "session_id", "created_at"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
    )