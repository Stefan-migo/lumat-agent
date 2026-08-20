"""ORM models mapping the migrated schema (design Data Model, 10 tables).

The schema is created by `db/migrations/001_init.sql` — SQLAlchemy maps to the
existing tables and never runs `create_all`. Enums mirror the PG enum types
created by the migration (labels must match exactly).
"""

import enum
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, REAL
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# Embedding dimensionality, local fastembed (db/migrations/008_local_embeddings.sql
# resized the column from 1536 to 384; keep in sync with kb.EMBED_DIMS).
EMBED_DIMS = 384


def _ts() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


def pg_enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    """PG-native Enum that stores the *member values* (labels in 001_init.sql).

    SQLAlchemy's default `Enum` persists member NAMES ("NUEVO") unless told
    otherwise; the migration creates the enum with lowercase labels, so we map
    values explicitly.
    """
    return Enum(
        enum_cls,
        name=name,
        create_type=False,
        values_callable=lambda members: [m.value for m in members],
    )


# ---------------------------------------------------------------------------
# Enums (labels must match db/migrations/001_init.sql CREATE TYPE)
# ---------------------------------------------------------------------------

class CustomerState(str, enum.Enum):
    NUEVO = "nuevo"
    CONTACTADO = "contactado"
    PENDIENTE = "pendiente"
    AGENDADO = "agendado"
    EN_EVALUACION = "en_evaluacion"
    FINALIZADO = "finalizado"
    CANCELADO = "cancelado"
    POSTVENTA = "postventa"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    OPERADOR = "operador"


class ConversationState(str, enum.Enum):
    BOT = "bot"
    HUMAN = "human"
    CLOSED = "closed"


class MessageDirection(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACTS = "contacts"
    OTHER = "other"


class MessageStatus(str, enum.Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class DocumentFormat(str, enum.Enum):
    PDF = "pdf"
    MD = "md"
    CSV = "csv"


class MemoryType(str, enum.Enum):
    DECISION = "decision"
    DISCOVERY = "discovery"
    PATTERN = "pattern"
    PREFERENCE = "preference"
    CUSTOMER_MEMO = "customer_memo"
    SUMMARY = "summary"
    SESSION = "session"
    PROMPT = "prompt"


class MemoryStatus(str, enum.Enum):
    ACTIVE = "active"
    NEEDS_REVIEW = "needs_review"
    ARCHIVED = "archived"


class ObservationType(str, enum.Enum):
    RECURRENCIA = "recurrencia"
    SIN_RESPUESTA = "sin_respuesta"
    RIESGO = "riesgo"
    OPORTUNIDAD = "oportunidad"


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone_e164: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(200))
    comuna: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(Text)
    state: Mapped[CustomerState] = mapped_column(
        pg_enum(CustomerState, "customer_state"),
        default=CustomerState.NUEVO,
        server_default="nuevo",
    )
    consent_status: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _ts()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        pg_enum(UserRole, "user_role"),
        default=UserRole.OPERADOR,
        server_default="operador",
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    failed_logins: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("idx_conversations_customer_id", "customer_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customers.id"), nullable=False
    )
    wa_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    state: Mapped[ConversationState] = mapped_column(
        pg_enum(ConversationState, "conversation_state"),
        default=ConversationState.BOT,
        server_default="bot",
    )
    summary: Mapped[str | None] = mapped_column(Text)
    captured_data: Mapped[dict | None] = mapped_column(JSONB)  # 003: CM-2 capture state
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _ts()
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_conversation_id", "conversation_id"),
        # mirrors the partial unique index from the migration (WH-5)
        Index(
            "uq_messages_wamid_inbound",
            "wamid",
            unique=True,
            postgresql_where="direction = 'inbound' AND wamid IS NOT NULL",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    wamid: Mapped[str | None] = mapped_column(String(255))
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("conversations.id"), nullable=False
    )
    direction: Mapped[MessageDirection] = mapped_column(
        pg_enum(MessageDirection, "message_direction"),
        nullable=False,
    )
    msg_type: Mapped[MessageType] = mapped_column(
        pg_enum(MessageType, "message_type"),
        default=MessageType.TEXT,
        server_default="text",
    )
    text: Mapped[str | None] = mapped_column(Text)
    media_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[MessageStatus] = mapped_column(
        pg_enum(MessageStatus, "message_status"),
        default=MessageStatus.RECEIVED,
        server_default="received",
    )
    payload: Mapped[dict | None] = mapped_column(JSONB)
    cost_llm: Mapped[float | None] = mapped_column(Numeric(12, 6))
    cost_meta: Mapped[float | None] = mapped_column(Numeric(12, 6))
    created_at: Mapped[datetime] = _ts()


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        Index("idx_cases_conversation_id", "conversation_id"),
        Index("idx_cases_customer_id", "customer_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("conversations.id"), nullable=False
    )
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customers.id"), nullable=False
    )
    # 007: created_at (panel ordering + KPI windows, T5.3/T5.5).
    created_at: Mapped[datetime] = _ts()
    service: Mapped[str | None] = mapped_column(String(100))
    priority: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str | None] = mapped_column(String(50))
    emergency: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    responsible_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    summary: Mapped[str | None] = mapped_column(Text)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 005: EM-4 notification state (T4.3) — notified_at set when the owner/
    # technician notification was delivered on ANY channel (whatsapp/email);
    # the reminder sweep keys off it. acknowledged_at/ack_by record the ack.
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ack_by: Mapped[str | None] = mapped_column(String(100))
    reminder_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # 006: HH-2 deriva bundle snapshot (history + summary + customer +
    # captured fields), built by the handoff node at escalation time.
    bundle: Mapped[dict | None] = mapped_column(JSONB)


class CustomerNote(Base):
    """Internal staff note on a customer ficha (CR-4; 002_customer_notes.sql).

    Staff-only (admin/operador) — never exposed to the customer. The schema
    keeps notes out of the `customers` row on purpose (CR-4: visible to staff
    only); the panel renders them from this table.
    """

    __tablename__ = "customer_notes"
    __table_args__ = (
        Index("idx_customer_notes_customer_id", "customer_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customers.id"), nullable=False
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = _ts()


class ConversationEvent(Base):
    __tablename__ = "conversation_events"
    __table_args__ = (
        Index("idx_conversation_events_conversation_id", "conversation_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("conversations.id"), nullable=False
    )
    event: Mapped[str] = mapped_column(String(100), nullable=False)
    cause: Mapped[str | None] = mapped_column(Text)
    # 006: HH-1 transition actor (system | bot | rule); NULL for pre-006 rows.
    actor: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = _ts()


class KbDocument(Base):
    __tablename__ = "kb_documents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    format: Mapped[DocumentFormat] = mapped_column(
        pg_enum(DocumentFormat, "document_format"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    active_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    provider: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str | None] = mapped_column(String(100))
    cost_meta: Mapped[float | None] = mapped_column(Numeric(12, 6))
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class KbChunk(Base):
    __tablename__ = "kb_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "version", "chunk_index"),
        Index("idx_kb_chunks_document_id", "document_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("kb_documents.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_meta: Mapped[dict | None] = mapped_column(JSONB)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIMS), nullable=False)


class Memory(Base):
    """Persistent, domain-aware memory row (099_memory.sql, MEM-1).

    Typed memories keyed by (proyecto, scope, entity_id, topic_key) with a 384d
    local embedding for hybrid vector+FTS recall (MEM-3). Only proyecto='default'
    is writable (MEM-2, enforced in app/services/memory.py).
    """

    __tablename__ = "memories"
    __table_args__ = (
        UniqueConstraint("proyecto", "scope", "entity_id", "topic_key"),
        Index("idx_memories_entity", "scope", "entity_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    proyecto: Mapped[str] = mapped_column(String(100), default="default", server_default="default")
    scope: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[MemoryType] = mapped_column(
        pg_enum(MemoryType, "memory_type"),
        default=MemoryType.DECISION,
        server_default="decision",
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIMS), nullable=False)
    topic_key: Mapped[str] = mapped_column(String(255), default="general", server_default="general")
    pin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    review_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[MemoryStatus] = mapped_column(
        pg_enum(MemoryStatus, "memory_status"),
        default=MemoryStatus.ACTIVE,
        server_default="active",
    )
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MemoryRelation(Base):
    """Schema-only relation between two memory rows (Ponytail deferral).

    No consumer until the relations worker lands; kept to match migration 009
    (MEM-1 creates the table). Do not write relations here before S3.
    """

    __tablename__ = "memory_relations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_a: Mapped[int] = mapped_column(BigInteger, ForeignKey("memories.id"), nullable=False)
    id_b: Mapped[int] = mapped_column(BigInteger, ForeignKey("memories.id"), nullable=False)
    relation: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(REAL, default=1.0, server_default="1.0")
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts()


class MemoryObservation(Base):
    """Typed observation linked to a memory (MEM-5; 099_memory.sql)."""

    __tablename__ = "memory_observations"
    __table_args__ = (
        Index("idx_memory_observations_entity", "scope", "entity_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    memory_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("memories.id"))
    scope: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[ObservationType] = mapped_column(
        pg_enum(ObservationType, "observation_type"),
        nullable=False,
    )
    detalle: Mapped[dict] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = _ts()


class Settings(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(100))
    before: Mapped[dict | None] = mapped_column(JSONB)
    after: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = _ts()
