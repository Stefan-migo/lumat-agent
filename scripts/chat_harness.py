"""Channel-less manual exercise surface for the WhatsApp conversation brain.

Why this exists
---------------
Meta Cloud API onboarding is blocked on client credentials, so the customer
bot cannot be driven end to end. This harness drives the **real** entry point,
`app.chat.graph.run_conversation`, from a terminal: same state rebuild, same
deterministic gates, same orchestration, same memory writes, same KB
retrieval. It performs no HTTP and references no Meta identifier.

What it deliberately does NOT do
--------------------------------
It reuses `run_conversation` unmodified — it adds no production seam. That
means it also skips the channel-coupled wrapper `webhook.ingest.process_message`:
Meta media download, the emergency ack, the human/closed guard and
`deliver_outbound`. Replies are persisted and printed, never sent. So this
exercises the **brain**, not the WhatsApp plumbing.

Usage
-----
    # inside the api container, so it shares the app's env and database
    docker compose -p lumat-odd-chat-harness -f infra/docker-compose.yml \
        -f infra/docker-compose.harness.yml exec api \
        uv run python scripts/chat_harness.py --phone +56900000001

Conversations written here are plain `conversations`/`messages` rows, so the
panel of the same stack renders them (refresh by hand: the realtime publisher
is process-local, see D2 in `odd/tasks/chat-harness.md`).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Runnable both as `python scripts/chat_harness.py` (sys.path[0] is scripts/)
# and as an importable module from the integration suite.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.chat.graph import run_conversation  # noqa: E402
from app.chat.state import get_or_create_conversation  # noqa: E402
from app.db import session_scope  # noqa: E402
from app.models import (  # noqa: E402
    Case,
    Conversation,
    ConversationEvent,
    Memory,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.customers import get_or_create_customer  # noqa: E402

__all__ = ["ensure_conversation", "inspect", "run_turn"]

DEFAULT_PHONE = "+56900000001"
_EXIT_WORDS = {"salir", "exit", "quit"}


# ---------------------------------------------------------------------------
# Core — the testable contract (see tests/integration/test_chat_harness.py)
# ---------------------------------------------------------------------------


def ensure_conversation(session: Session, phone: str) -> int:
    """Return the open conversation id for `phone`, creating it when absent.

    Delegates to the same services the webhook uses, so a closed conversation
    is never reopened: a later call opens a new one on the same customer
    (CR-5). Idempotent for an already-open conversation.
    """
    customer = get_or_create_customer(session, phone)
    conversation = get_or_create_conversation(session, customer, phone)
    return conversation.id


def run_turn(session: Session, conversation_id: int, text: str) -> list[str]:
    """Persist one inbound customer message and run the conversation brain.

    The persist and the run are separate committed steps on purpose: the graph
    nodes open their own sessions and write back onto the inbound row (LLM cost
    is accumulated on the message). Flushing without committing would hold a
    row lock on that message and the node's session would block forever. This
    is the same persist-then-process boundary as the webhook (WH-4), where
    `ingest_payload` commits before `process_message` runs.
    """
    message = Message(
        wamid=f"harness.{uuid4().hex}",
        conversation_id=conversation_id,
        direction=MessageDirection.INBOUND,
        msg_type=MessageType.TEXT,
        text=text,
        status=MessageStatus.RECEIVED,
    )
    session.add(message)
    session.flush()
    # The panel's active conversation list filters on `last_message_at IS NOT
    # NULL` and orders by it (`app/panel/api/routes/conversations.py:238-241`).
    # `webhook.ingest.persist_message` stamps it when it persists an inbound
    # message (`app/webhook/ingest.py:268-272`); skipping it here would produce
    # conversations that never appear in the panel this harness exists to feed.
    conversation = session.get(Conversation, conversation_id)
    if conversation is not None:
        conversation.last_message_at = datetime.now(timezone.utc)
    session.commit()
    return run_conversation(session, message)


def inspect(session: Session, conversation_id: int) -> dict:
    """Return everything the brain left observable for one conversation.

    The classified intent is not a column on `conversations`; it is recorded
    from inside the production path as a `conversation_events` row
    (`classified`, cause `intent:<intent>` — `app/chat/nodes/classify_intent.py`),
    and an unrecognised intent records `unknown_intent` instead. Reading those
    rows is why the harness can stay faithful to `run_conversation` and still
    show what the brain decided.
    """
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        raise ValueError(f"unknown conversation {conversation_id}")

    case = session.scalar(
        select(Case)
        .where(Case.conversation_id == conversation_id)
        .order_by(Case.id.desc())
        .limit(1)
    )
    events = session.scalars(
        select(ConversationEvent)
        .where(ConversationEvent.conversation_id == conversation_id)
        .order_by(ConversationEvent.created_at, ConversationEvent.id)
    ).all()
    memories = session.scalars(
        select(Memory)
        .where(
            Memory.scope == "customer",
            Memory.entity_id == str(conversation.customer_id),
        )
        .order_by(Memory.id)
    ).all()
    messages = session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id)
    ).all()

    return {
        "conversation_id": conversation.id,
        "state": conversation.state.value,
        "captured_data": conversation.captured_data,
        "summary": conversation.summary,
        "case": _case_row(case),
        "events": [
            {
                "event": row.event,
                "cause": row.cause,
                "actor": row.actor,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in events
        ],
        "memories": [
            {
                "topic_key": row.topic_key,
                "tipo": row.tipo.value if hasattr(row.tipo, "value") else str(row.tipo),
                "status": row.status.value if hasattr(row.status, "value") else str(row.status),
                "contenido": row.contenido,
            }
            for row in memories
        ],
        "messages": [
            {
                "direction": row.direction.value,
                "text": row.text,
                "status": row.status.value if row.status else None,
            }
            for row in messages
        ],
    }


def _case_row(case: Case | None) -> dict | None:
    if case is None:
        return None
    return {
        "id": case.id,
        "status": case.status,
        "priority": case.priority,
        "emergency": bool(case.emergency),
        "service": case.service,
    }


# ---------------------------------------------------------------------------
# Interactive shell — I/O glue, deliberately not unit-tested
# ---------------------------------------------------------------------------


def _intent_of(events: list[dict], since: int) -> str | None:
    """Latest classified/unknown intent among the events added this turn."""
    for event in reversed(events[since:]):
        if event["event"] == "classified" and event["cause"]:
            return event["cause"].removeprefix("intent:")
        if event["event"] == "unknown_intent":
            return "unknown"
    return None


def _status_line(snapshot: dict, events: list[dict], since: int) -> str:
    parts = [f"state={snapshot['state']}"]
    intent = _intent_of(events, since)
    parts.append(f"intent={intent}" if intent else "intent=-")
    parts.append(f"case=#{snapshot['case']['id']}" if snapshot["case"] else "case=-")
    topic_keys = ",".join(memory["topic_key"] for memory in snapshot["memories"])
    parts.append(f"memoria={topic_keys or '-'}")
    if snapshot["captured_data"]:
        parts.append(f"capturado={','.join(snapshot['captured_data'])}")
    return " · ".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exercise the Lumat conversation brain.")
    parser.add_argument("--phone", default=DEFAULT_PHONE, help="Customer phone (E.164).")
    parser.add_argument(
        "--conversation", type=int, default=None, help="Resume an existing conversation id."
    )
    args = parser.parse_args(argv)

    with session_scope() as session:
        conversation_id = args.conversation or ensure_conversation(session, args.phone)
        snapshot = inspect(session, conversation_id)

    print(f"lumat-harness · conversación #{conversation_id} · {args.phone}")
    print(f"state={snapshot['state']} · escribe como el cliente · 'salir' o Ctrl-D termina\n")

    seen_events = len(snapshot["events"])
    while True:
        try:
            text = input("cliente> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text.lower() in _EXIT_WORDS:
            break

        with session_scope() as session:
            replies = run_turn(session, conversation_id, text)
        with session_scope() as session:
            snapshot = inspect(session, conversation_id)

        for reply in replies:
            print(f"  bot | {reply}")
        if not replies:
            print("  bot | (sin respuesta)")
        print(f"  ── {_status_line(snapshot, snapshot['events'], seen_events)}\n")
        seen_events = len(snapshot["events"])

    with session_scope() as session:
        final = inspect(session, conversation_id)
    print(f"fin · state={final['state']} · mensajes={len(final['messages'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
