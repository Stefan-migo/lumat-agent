"""S3 integration tests — close event memo + observations (MEM-4, MEM-5, CM-9).

Scenarios mapped 1:1 from openspec/specs:

- MEM-4 "Close writes memo": a conversation that transitions to CLOSED via
  `set_conversation_state` upserts a customer_memo under the customer, reusing
  the CM-5 acta content (conversation.summary) verbatim.
- CM-9 "Close triggers memo": the close handler consumes the acta, it does not
  rewrite it.
- MEM-5 "Observation persisted": the patterns fire at close producing a
  `memory_observations` row with type + detail.
- MEM-5 "Recurrence threshold": recurrencia appears only when the configured
  window/count is reached.
- Patterns: sin_respuesta (inbound w/o bot reply within the configured hours),
  riesgo (escalated emergency case), oportunidad (case still without a ticket).

The observación criteria use the design thresholds exposed as configurable
constants in `Settings` (OBS_RECUR_WINDOW/OBS_RECUR_COUNT/OBS_NO_REPLY_HOURS) —
flagged for product sanity before S3 is merged (open design question).

Runs against the migrated pgvector test DB with the deterministic fake
embedder (autouse in tests/integration/conftest.py). Most tests call
`set_conversation_state` directly — the panel owns the close action in T5.3 and
the close hook lives in that helper, so we exercise the same production path.
"""

from types import SimpleNamespace

import psycopg
import pytest
from sqlalchemy import select

from app.chat.state import (  # noqa: E402
    get_or_create_conversation,
    set_conversation_state,
)
from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Case,
    Conversation,
    ConversationState as ConvState,
    MemoryType,
    MemoryObservation,
    MemoryRelation,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
    ObservationType,
)
from app.services import memory as memory_service  # noqa: E402
from app.services import tukulpan  # noqa: E402
from app.services.customers import get_or_create_customer  # noqa: E402
from _testdb import admin_database_url  # noqa: E402

ADMIN_DB_URL = admin_database_url()

ACTA = (
    "Acta: cliente con calefont en Providencia, se solicita visita tecnica "
    "para la proxima semana."
)


@pytest.fixture(autouse=True)
def clean_db(migrated_db):
    """Reset chat + memory tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(
            "TRUNCATE memories, memory_observations, memory_relations, "
            "settings, audit_log, conversation_events, cases, messages, "
            "conversations, customer_notes, customers RESTART IDENTITY CASCADE"
        )
    yield


def _start_conversation(
    summary: str | None = None,
    phone: str = "+56912345678",
) -> tuple[int, int]:
    """Create a customer + open conversation; returns (conversation, customer)."""
    with SessionLocal() as session:
        customer = get_or_create_customer(session, phone)
        conv = get_or_create_conversation(session, customer, phone)
        if summary is not None:
            conv.summary = summary
        session.commit()
        return conv.id, customer.id


def _close(conv_id: int, cause: str = "resolved") -> None:
    """Transition the conversation to CLOSED through the production helper."""
    with SessionLocal() as session:
        conv = session.get(Conversation, conv_id)
        set_conversation_state(session, conv, ConvState.CLOSED, cause=cause)
        session.commit()


def _add_inbound(conv_id: int, text: str, *, wamid: str = "wamid.s3") -> None:
    from datetime import datetime, timedelta, timezone

    with SessionLocal() as session:
        session.add(
            Message(
                wamid=wamid,
                conversation_id=conv_id,
                direction=MessageDirection.INBOUND,
                msg_type=MessageType.TEXT,
                text=text,
                status=MessageStatus.RECEIVED,
                created_at=datetime.now(timezone.utc) - timedelta(hours=3),
            )
        )
        session.commit()


def _memo_text(customer_id: int) -> str | None:
    with SessionLocal() as session:
        rows = memory_service.list_for_entity(
            session, scope="customer", entity_id=str(customer_id)
        )
        for m in rows:
            if m.topic_key == "customer_memo":
                return m.contenido
        return None


def _obs(customer_id: int, tipo: ObservationType) -> list:
    from app.models import MemoryObservation

    with SessionLocal() as session:
        return list(
            session.execute(
                select(MemoryObservation).where(
                    MemoryObservation.scope == "customer",
                    MemoryObservation.entity_id == str(customer_id),
                    MemoryObservation.tipo == tipo,
                )
            ).scalars()
        )


# ---------------------------------------------------------------------------
# MEM-4 / CM-9 — close writes the customer memo reusing the acta verbatim
# ---------------------------------------------------------------------------


def test_s3_close_writes_customer_memo_verbatim():
    conv_id, customer_id = _start_conversation(summary=ACTA)

    _close(conv_id)

    assert _memo_text(customer_id).endswith(f": {ACTA}")  # acta is preserved in a dated entry


def test_s3_close_accumulates_dated_customer_memo_entries():
    conv1, customer_id = _start_conversation(summary="Acta uno")
    _close(conv1)
    conv2, same_customer = _start_conversation(summary="Acta dos")
    assert same_customer == customer_id
    _close(conv2)

    memo = _memo_text(customer_id)
    assert memo is not None
    assert memo.endswith(": Acta dos")
    assert ": Acta uno" in memo
    assert memo.index(": Acta uno") < memo.index(": Acta dos")
    assert len(memo.splitlines()) == 2
    assert all(
        line[:10].count("-") == 2 and line[10:12] == ": "
        for line in memo.splitlines()
    )


def test_s3_close_without_acta_preserves_existing_memo():
    conv1, customer_id = _start_conversation(summary="Acta previa")
    _close(conv1)
    previous = _memo_text(customer_id)
    # Same phone on purpose: the second close must land on the SAME customer, or
    # the test reads a memo the close never wrote and passes without the fix.
    conv2, same_customer = _start_conversation(summary=None)
    assert same_customer == customer_id

    _close(conv2)

    assert _memo_text(customer_id) == previous


def test_s3_close_with_new_acta_appends_instead_of_replacing_existing_memo():
    conv_id, customer_id = _start_conversation(summary="Acta actual")
    with SessionLocal() as session:
        memory_service.upsert(
            session,
            scope="customer",
            entity_id=str(customer_id),
            topic_key="customer_memo",
            tipo=MemoryType.CUSTOMER_MEMO,
            titulo="customer_memo",
            contenido="Memo previa",
        )
        session.commit()

    _close(conv_id)

    memo = _memo_text(customer_id)
    assert memo is not None
    assert memo.startswith("Memo previa\n")
    assert memo.endswith(": Acta actual")


def test_s3_close_without_any_acta_does_not_create_empty_memo():
    conv_id, customer_id = _start_conversation(summary=None)

    _close(conv_id)

    assert _memo_text(customer_id) is None


def test_s3_close_memo_cap_drops_whole_old_entries():
    conv_ids = []
    for index in range(5):
        conv_id, _ = _start_conversation(
            summary=f"{index}" + ("x" * 999),
        )
        conv_ids.append(conv_id)
    for conv_id in conv_ids:
        _close(conv_id)

    memo = _memo_text(1)
    assert memo is not None
    assert len(memo) <= 3_000
    assert memo.endswith(": " + "4" + ("x" * 999))
    assert "0" + ("x" * 999) not in memo
    assert all(len(line.split(": ", 1)[1]) == 1000 for line in memo.splitlines())


# ---------------------------------------------------------------------------
# T2 / S4 — bounded per-turn session memory
# ---------------------------------------------------------------------------


def test_session_memory_cap_drops_whole_old_turns_and_keeps_latest():
    with SessionLocal() as session:
        for index in range(1, 41):
            tukulpan.persist_memory_session(
                session,
                SimpleNamespace(
                    customer_id=77,
                    window=[
                        {"direction": "inbound", "text": f"turn-{index:02d}: " + "x" * 60}
                    ],
                ),
            )
        session.commit()
        memory = memory_service.get_by_key(
            session, scope="customer", entity_id="77", topic_key="session"
        )

    assert memory is not None
    assert len(memory.contenido) <= 2_000
    assert "turn-01:" not in memory.contenido
    assert memory.contenido.endswith("turn-40: " + "x" * 60)


# ---------------------------------------------------------------------------
# T3 / S5 — bounded customer context
# ---------------------------------------------------------------------------


def test_customer_context_is_empty_without_memories():
    with SessionLocal() as session:
        assert tukulpan.load_customer_context(session, 999) == ""


def test_customer_context_budget_prioritizes_pin_then_last_seen():
    from datetime import datetime, timedelta, timezone

    with SessionLocal() as session:
        for index in range(20):
            row = tukulpan.upsert(
                session,
                scope="customer",
                entity_id="88",
                topic_key=f"memory-{index:02d}",
                tipo=MemoryType.CUSTOMER_MEMO,
                titulo=f"memory-{index:02d}",
                contenido=f"entry-{index:02d}-" + ("x" * 490),
                pin=index == 0,
            )
            row.last_seen_at = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(
                days=index
            )
        session.flush()
        context = tukulpan.load_customer_context(session, 88)

    assert len(context) <= 1_500
    assert "entry-00-" in context
    assert "entry-19-" in context
    assert context.index("entry-00-") < context.index("entry-19-")
    if "entry-18-" in context:
        assert context.index("entry-19-") < context.index("entry-18-")


# ---------------------------------------------------------------------------
# T4 / S6 — recurring observations update one JSONB row
# ---------------------------------------------------------------------------


def test_observation_recurrence_increments_existing_row():
    from app.models import MemoryObservation

    with SessionLocal() as session:
        tukulpan._write_observation(
            session, 99, ObservationType.RECURRENCIA, {"last_seen": "first"}
        )
        tukulpan._write_observation(
            session, 99, ObservationType.RECURRENCIA, {"last_seen": "second"}
        )
        rows = list(
            session.execute(
                select(MemoryObservation).where(
                    MemoryObservation.scope == "customer",
                    MemoryObservation.entity_id == "99",
                    MemoryObservation.tipo == ObservationType.RECURRENCIA,
                )
            ).scalars()
        )

    assert len(rows) == 1
    assert rows[0].detalle["occurrences"] == 2
    assert rows[0].detalle["last_seen"] != "first"


# ---------------------------------------------------------------------------
# MEM-5 — typed observations on close
# ---------------------------------------------------------------------------


def test_s3_no_recurrencia_below_threshold():
    """A single close produces no recurrencia observation (MEM-5 threshold)."""
    conv_id, customer_id = _start_conversation(summary=ACTA)
    _close(conv_id)

    assert _obs(customer_id, ObservationType.RECURRENCIA) == []


def test_s3_recurrencia_fires_at_threshold():
    """A second close within the window raises a recurrencia observation."""
    conv1, customer_id = _start_conversation(summary=ACTA, phone="+56911111111")
    _close(conv1)
    conv2, _ = _start_conversation(summary=ACTA, phone="+56911111111")
    _close(conv2)

    assert len(_obs(customer_id, ObservationType.RECURRENCIA)) == 1


def test_s3_sin_respuesta_on_unanswered_inbound():
    """An inbound with no bot reply within the window yields sin_respuesta."""
    conv_id, customer_id = _start_conversation(summary=ACTA)
    _add_inbound(conv_id, "necesito ayuda con mi caldera")

    _close(conv_id)

    assert len(_obs(customer_id, ObservationType.SIN_RESPUESTA)) == 1


def test_s3_no_sin_respuesta_when_bot_replied():
    """An inbound that got a subsequent bot reply yields no sin_respuesta."""
    conv_id, customer_id = _start_conversation(summary=ACTA)
    _add_inbound(conv_id, "necesito ayuda con mi caldera", wamid="wamid.asked")
    with SessionLocal() as session:
        session.add(
            Message(
                wamid="wamid.answered",
                conversation_id=conv_id,
                direction=MessageDirection.OUTBOUND,
                msg_type=MessageType.TEXT,
                text="Claro, un momento por favor.",
                status=MessageStatus.PROCESSED,
            )
        )
        session.commit()

    _close(conv_id)

    # the outbound reply follows the inbound, so the customer was answered
    assert _obs(customer_id, ObservationType.SIN_RESPUESTA) == []


def test_s3_riesgo_on_flaged_emergency_case():
    """An escalated emergency case yields a riesgo observation on close."""
    conv_id, customer_id = _start_conversation(summary=ACTA)
    with SessionLocal() as session:
        case = Case(
            conversation_id=conv_id,
            customer_id=customer_id,
            emergency=True,
            status="escalado",
        )
        session.add(case)
        session.commit()

    _close(conv_id)

    assert len(_obs(customer_id, ObservationType.RIESGO)) == 1


def test_s3_no_riesgo_without_emergency_flag():
    """A normal (non-emergency) case yields no riesgo observation."""
    conv_id, customer_id = _start_conversation(summary=ACTA)
    with SessionLocal() as session:
        case = Case(
            conversation_id=conv_id,
            customer_id=customer_id,
            emergency=False,
            status="abierto",
        )
        session.add(case)
        session.commit()

    _close(conv_id)

    assert _obs(customer_id, ObservationType.RIESGO) == []


def test_s3_oportunidad_on_case_without_ticket():
    """A case still open with no ticket yields an oportunidad observation."""
    conv_id, customer_id = _start_conversation(summary=ACTA)
    _add_inbound(conv_id, "me interesa conocer los valores de mantenimiento")

    _close(conv_id)

    assert len(_obs(customer_id, ObservationType.OPORTUNIDAD)) == 1


def test_s3_no_oportunidad_when_ticket_issued():
    """A case with a ticket issued yields no oportunidad observation."""
    conv_id, customer_id = _start_conversation(summary=ACTA)
    with SessionLocal() as session:
        case = Case(
            conversation_id=conv_id,
            customer_id=customer_id,
            emergency=False,
            status="resuelto",
        )
        session.add(case)
        session.commit()

    _close(conv_id)

    assert _obs(customer_id, ObservationType.OPORTUNIDAD) == []


def test_s3_multiline_acta_stays_one_entry():
    """An acta with newlines must still be ONE entry.

    The memo is a line-per-entry store trimmed with splitlines, so a multi-line
    acta would be split by the next close and the cap could drop half an entry.
    """
    conv, customer_id = _start_conversation(summary="Primera linea\nSegunda linea")
    _close(conv)

    memo = _memo_text(customer_id)

    assert memo.count("\n") == 0, memo
    assert "Primera linea Segunda linea" in memo


def test_s5_single_oversized_memory_is_truncated_not_dropped():
    """The only memory a customer has must not vanish because it is too big.

    Dropping it would hand the model an empty context while we hold a memory.
    """
    _, customer_id = _start_conversation()
    with SessionLocal() as session:
        tukulpan.upsert(
            session,
            scope="customer",
            entity_id=str(customer_id),
            topic_key="ficha",
            tipo=MemoryType.DISCOVERY,
            titulo="ficha",
            contenido="x" * 5000,
        )
        session.commit()
        context = tukulpan.load_customer_context(session, customer_id)

    assert context, "an oversized memory must not vanish from the context"
    assert len(context) <= tukulpan.MEMORY_CONTEXT_MAX_CHARS
    assert context.endswith("…")


def test_s1_empty_acta_close_leaves_memo_row_and_relations_untouched():
    """S1/AC1: an empty acta leaves the memo row byte-identical, relations included."""
    conv1, customer_id = _start_conversation(summary="Acta previa")
    _close(conv1)
    with SessionLocal() as session:
        memo = tukulpan.get_by_key(
            session, scope="customer", entity_id=str(customer_id), topic_key="customer_memo"
        )
        other = tukulpan.upsert(
            session,
            scope="customer",
            entity_id=str(customer_id),
            topic_key="otra",
            tipo=MemoryType.DISCOVERY,
            titulo="otra",
            contenido="otra memoria",
        )
        session.flush()
        session.add(MemoryRelation(id_a=memo.id, id_b=other.id, relation="related",
                                   confidence=0.9, source="judge"))
        session.commit()
        before = (memo.contenido, memo.last_seen_at, memo.updated_at, memo.origin_thread_id)

    conv2, same_customer = _start_conversation(summary=None)
    assert same_customer == customer_id
    _close(conv2)

    with SessionLocal() as session:
        memo = tukulpan.get_by_key(
            session, scope="customer", entity_id=str(customer_id), topic_key="customer_memo"
        )
        assert (memo.contenido, memo.last_seen_at, memo.updated_at, memo.origin_thread_id) == before


def test_s3_a_single_acta_longer_than_the_cap_is_truncated_not_overflowed():
    """S3/AC3: the newest acta survives even when it alone exceeds the budget."""
    conv, customer_id = _start_conversation(summary="V" * 4000)
    _close(conv)

    memo = _memo_text(customer_id)

    assert len(memo) <= tukulpan.CUSTOMER_MEMO_MAX_CHARS
    assert memo.endswith("…")


def test_s3_a_legacy_multiline_memo_is_read_as_one_entry():
    """S3: a memo the old writer stored with newlines must not be cut in half."""
    _, customer_id = _start_conversation()
    legacy = "V" * 1600 + "\n" + "W" * 1600
    with SessionLocal() as session:
        tukulpan.upsert(
            session,
            scope="customer",
            entity_id=str(customer_id),
            topic_key="customer_memo",
            tipo=MemoryType.CUSTOMER_MEMO,
            titulo="customer_memo",
            contenido=legacy,
        )
        session.commit()

    assert tukulpan._memo_entries(legacy) == [legacy]


def test_s4_session_a_single_turn_longer_than_the_cap_is_truncated():
    """S4/AC4: one huge message must not push the session past its budget."""
    _, customer_id = _start_conversation()
    with SessionLocal() as session:
        tukulpan.persist_memory_session(
            session,
            SimpleNamespace(
                customer_id=customer_id,
                window=[{"direction": "inbound", "text": "x" * 2500}],
            ),
        )
        session.commit()
        session_memory = tukulpan.get_by_key(
            session, scope="customer", entity_id=str(customer_id), topic_key="session"
        )

    assert len(session_memory.contenido) <= tukulpan.SESSION_MAX_CHARS
    assert session_memory.contenido.endswith("…")


def test_s6_observation_dedups_a_row_written_without_last_seen():
    """S6: a legacy observation row (no detalle.last_seen) still dedups."""
    with SessionLocal() as session:
        session.add(
            MemoryObservation(
                scope="customer",
                entity_id="98",
                tipo=ObservationType.RECURRENCIA,
                detalle={"window_days": 30},
            )
        )
        session.commit()
        tukulpan._write_observation(session, 98, ObservationType.RECURRENCIA, {"window_days": 30})
        session.commit()
        rows = list(session.scalars(select(MemoryObservation).where(MemoryObservation.entity_id == "98")))

    assert len(rows) == 1
    assert rows[0].detalle["occurrences"] == 2
    assert rows[0].detalle["window_days"] == 30
