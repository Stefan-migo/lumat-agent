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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, REAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    TECNICO = "tecnico"


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


class DeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    UNKNOWN = "unknown"


class DocumentFormat(str, enum.Enum):
    PDF = "pdf"
    MD = "md"
    CSV = "csv"


class KbVisibility(str, enum.Enum):
    CUSTOMER = "customer"
    INTERNAL = "internal"


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


class MemoryProducer(str, enum.Enum):
    USER = "user"
    SYSTEM = "system"
    AGENT = "agent"
    PIPELINE = "pipeline"


class MemoryVisibility(str, enum.Enum):
    THREAD = "thread"
    PROJECT = "project"


class AppointmentStatus(str, enum.Enum):
    BOOKED = "booked"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class ObservationType(str, enum.Enum):
    RECURRENCIA = "recurrencia"
    SIN_RESPUESTA = "sin_respuesta"
    RIESGO = "riesgo"
    OPORTUNIDAD = "oportunidad"


class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    purpose: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(
        String(20),
        default=ProjectStatus.ACTIVE,
        server_default="active",
        nullable=False,
    )
    purpose_embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIMS), nullable=False)
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ProjectAlias(Base):
    __tablename__ = "project_aliases"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id"), nullable=False)
    alias: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    created_at: Mapped[datetime] = _ts()


class ProjectAudit(Base):
    __tablename__ = "project_audit"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("projects.id"))
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    before: Mapped[dict | None] = mapped_column(JSONB)
    after: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = _ts()

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
        Index("idx_conversations_responsible_id", "responsible_id"),
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
    responsible_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
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
        Index(
            "uq_messages_outbound_request_id",
            "request_id",
            unique=True,
            postgresql_where="direction = 'outbound' AND request_id IS NOT NULL",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    wamid: Mapped[str | None] = mapped_column(String(255))
    author_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    request_id: Mapped[str | None] = mapped_column(String(255))
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
    delivery_status: Mapped[DeliveryStatus | None] = mapped_column(
        pg_enum(DeliveryStatus, "delivery_status")
    )
    delivery_error: Mapped[str | None] = mapped_column(Text)
    delivery_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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
    # 027: KB audience. `internal` is the fail-safe default: a document nobody
    # classified stays out of the customer-facing chatbot's reach.
    visibility: Mapped[KbVisibility] = mapped_column(
        pg_enum(KbVisibility, "kb_visibility"),
        nullable=False,
        default=KbVisibility.INTERNAL,
        server_default="'internal'",
    )
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
        Index(
            "uq_memories_normalized_content",
            "proyecto",
            "scope",
            "entity_id",
            "normalized_hash",
            unique=True,
            postgresql_where=text("normalized_hash IS NOT NULL"),
        ),
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
    normalized_hash: Mapped[str | None] = mapped_column(String(64))
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    pin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    review_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[MemoryStatus] = mapped_column(
        pg_enum(MemoryStatus, "memory_status"),
        default=MemoryStatus.ACTIVE,
        server_default="active",
    )
    producer: Mapped[MemoryProducer] = mapped_column(
        pg_enum(MemoryProducer, "memory_producer"),
        default=MemoryProducer.SYSTEM,
        server_default="system",
        nullable=False,
    )
    origin_thread_id: Mapped[str | None] = mapped_column(String(100))
    visibility: Mapped[MemoryVisibility] = mapped_column(
        pg_enum(MemoryVisibility, "memory_visibility"),
        default=MemoryVisibility.THREAD,
        server_default="thread",
        nullable=False,
    )
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MemoryRelation(Base):
    """A judged or human-resolved relation between two memory rows."""

    __tablename__ = "memory_relations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_a: Mapped[int] = mapped_column(BigInteger, ForeignKey("memories.id"), nullable=False)
    id_b: Mapped[int] = mapped_column(BigInteger, ForeignKey("memories.id"), nullable=False)
    relation: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(REAL, default=1.0, server_default="1.0")
    reason: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20), default="judge", server_default="judge")
    human_resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
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


class TechnicianAvailability(Base):
    __tablename__ = "technician_availability"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    technician_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index("idx_appointments_customer", "customer_id", "starts_at"),
        Index("idx_appointments_case", "case_id", "starts_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    service: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("customers.id"), nullable=False)
    case_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cases.id"), nullable=False)
    technician_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    local_start: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    timezone: Mapped[str] = mapped_column(String(100), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        pg_enum(AppointmentStatus, "appointment_status"),
        default=AppointmentStatus.BOOKED, server_default="booked",
    )
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    history: Mapped[list["AppointmentHistory"]] = relationship(
        back_populates="appointment", order_by="AppointmentHistory.created_at, AppointmentHistory.id"
    )
    calendar_sync: Mapped["AppointmentCalendarSync | None"] = relationship(
        back_populates="appointment", uselist=False
    )


class AppointmentHistory(Base):
    __tablename__ = "appointment_history"
    __table_args__ = (Index("idx_appointment_history_appointment", "appointment_id", "created_at", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    appointment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("appointments.id"), nullable=False)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    from_status: Mapped[AppointmentStatus | None] = mapped_column(pg_enum(AppointmentStatus, "appointment_status"))
    to_status: Mapped[AppointmentStatus] = mapped_column(pg_enum(AppointmentStatus, "appointment_status"), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = _ts()
    appointment: Mapped[Appointment] = relationship(back_populates="history")


class AppointmentCalendarSync(Base):
    __tablename__ = "appointment_calendar_sync"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    appointment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("appointments.id"), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, default="ics")
    uid: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    timezone: Mapped[str] = mapped_column(String(100), nullable=False)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    external_id: Mapped[str | None] = mapped_column(String(255))
    payload: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    appointment: Mapped[Appointment] = relationship(back_populates="calendar_sync")


class NotificationTemplateVersion(Base):
    __tablename__ = "notification_template_versions"
    __table_args__ = (UniqueConstraint("event", "channel", "locale", "version"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event: Mapped[str] = mapped_column(String(100), nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    locale: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    required_variables: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    approved: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    smtp_allowed: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = _ts()


class DomainEvent(Base):
    """Durable transactional event consumed by the bounded H4 worker."""

    __tablename__ = "domain_events"
    __table_args__ = (
        UniqueConstraint("dedupe_key"),
        Index("idx_domain_events_claim", "status", "available_at", "leased_until", "id"),
        Index("idx_domain_events_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    occurred_at: Mapped[datetime] = _ts()
    status: Mapped[str] = mapped_column(String(30), default="pending", server_default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    available_at: Mapped[datetime] = _ts()
    leased_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_owner: Mapped[str | None] = mapped_column(String(100))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)


class AutomationRule(Base):
    __tablename__ = "automation_rules"
    __table_args__ = (Index("idx_automation_rules_event", "event_type", "enabled"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    conditions: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    template_event: Mapped[str] = mapped_column(String(100), nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AutomationExecution(Base):
    __tablename__ = "automation_executions"
    __table_args__ = (
        UniqueConstraint("execution_key"),
        Index("idx_automation_executions_rule_time", "rule_id", "created_at"),
        Index("idx_automation_executions_event", "event_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("automation_rules.id"), nullable=False)
    event_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("domain_events.id"), nullable=False)
    execution_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    outcome: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    operation_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("notification_operations.id"))
    created_at: Mapped[datetime] = _ts()


class NotificationOperation(Base):
    __tablename__ = "notification_operations"
    __table_args__ = (Index("idx_notification_operations_due", "status", "next_attempt_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_entity: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    event_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("domain_events.id"))
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30), default="pending", server_default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    next_attempt_at: Mapped[datetime] = _ts()
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    attempts_log: Mapped[list["NotificationAttempt"]] = relationship(
        back_populates="operation", order_by="NotificationAttempt.id"
    )


class PanelNotification(Base):
    __tablename__ = "panel_notifications"
    __table_args__ = (UniqueConstraint("user_id", "operation_id"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    operation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("notification_operations.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _ts()
    operation: Mapped[NotificationOperation] = relationship()


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(Text, nullable=False)
    auth: Mapped[str] = mapped_column(Text, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class InternalChatThread(Base):
    __tablename__ = "internal_chat_threads"
    __table_args__ = (Index("idx_internal_chat_threads_user_updated", "user_id", "updated_at", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="open", server_default="open")
    assistant_state: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    current_plan: Mapped[dict | None] = mapped_column(JSONB)
    active_run_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class InternalChatMessage(Base):
    __tablename__ = "internal_chat_messages"
    __table_args__ = (Index("idx_internal_chat_messages_thread_created", "thread_id", "created_at", "id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("internal_chat_threads.id", ondelete="CASCADE"), nullable=False)
    author: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="processing", server_default="processing")
    error: Mapped[str | None] = mapped_column(Text)
    assistant_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    cost_llm: Mapped[float | None] = mapped_column(Numeric(12, 6))
    created_at: Mapped[datetime] = _ts()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssistantAttachment(Base):
    __tablename__ = "assistant_attachments"
    __table_args__ = (Index("idx_assistant_attachments_thread", "thread_id", "deleted_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("internal_chat_threads.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _ts()
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationAttempt(Base):
    __tablename__ = "notification_attempts"
    __table_args__ = (UniqueConstraint("operation_id", "attempt_number"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    operation_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("notification_operations.id"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = _ts()
    operation: Mapped[NotificationOperation] = relationship(back_populates="attempts_log")
