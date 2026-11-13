"""Extract durable owner promises without rewriting what the sender actually said.

The corpus measured 58 explicit owner promises, including work delivered late,
never delivered, or left open; summaries and conversation events do not preserve
that obligation. A small phrase table records the measured shapes deterministically,
and dates are stored only when the message states one rather than inferred.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Commitment, Conversation, Message
from app.services.settings import get_hours_timezone

_PROMISE_SHAPES = tuple(
    re.compile(pattern)
    for pattern in (
        r"\ble\s+envio\s+el\s+detalle\b",
        r"\bte\s+envio\b",
        r"\bmanana\s+voy\b",
        r"\ble\s+confirmo\b",
        r"\bestoy\s+cotizando\b",
        r"\blo\s+dejo\s+agendado\b",
        r"\bte\s+aviso\b",
        r"\ble\s+preparo\b",
        r"\bme\s+consigo\b",
        r"\bcoordino\b",
        r"\benviare\b",
        r"\bte\s+contacto\b",
        r"\blo\s+reviso\s+y\s+te\s+digo\b",
    )
)
_WEEKDAYS = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "domingo": 6,
}


def _fold(text: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", text.casefold())
        if unicodedata.category(character) != "Mn"
    )


def is_promise(text: str | None) -> bool:
    """Return whether text contains one of the corpus-measured promise shapes."""
    if not text:
        return False
    folded = _fold(text)
    return any(pattern.search(folded) for pattern in _PROMISE_SHAPES)


def promise_due(text: str, *, now: datetime) -> datetime | None:
    """Resolve an explicitly named date to local midnight in `now`'s timezone."""
    folded = _fold(text)
    if now.tzinfo is None:
        now = now.replace(tzinfo=ZoneInfo("America/Santiago"))
    local_now = now
    day = local_now.date()

    if re.search(r"\bpasado\s+manana\b", folded):
        due_day = day + timedelta(days=2)
    elif re.search(r"\bmanana\b", folded):
        due_day = day + timedelta(days=1)
    elif re.search(r"\bhoy\b", folded):
        due_day = day
    else:
        days_match = re.search(r"\ben\s+(\d+)\s+dias?\b", folded)
        if days_match:
            due_day = day + timedelta(days=int(days_match.group(1)))
        elif re.search(r"\bla\s+proxima\s+semana\b", folded):
            due_day = day + timedelta(days=(7 - day.weekday()))
        else:
            weekday_match = re.search(
                r"\bel\s+(lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b",
                folded,
            )
            if not weekday_match:
                return None
            target = _WEEKDAYS[weekday_match.group(1)]
            due_day = day + timedelta(days=(target - day.weekday()) % 7 or 7)

    return datetime.combine(due_day, time.min, tzinfo=local_now.tzinfo)


def _business_timezone(session: Session) -> ZoneInfo:
    name = get_hours_timezone(session)
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("America/Santiago")


def record_from_message(
    session: Session, message: Message, *, actor: str
) -> Commitment | None:
    """Store a promise once, verbatim, because 58 measured promises otherwise vanish from the work record."""
    if not is_promise(message.text):
        return None
    existing = session.scalar(
        select(Commitment).where(Commitment.source_message_id == message.id)
    )
    if existing is not None:
        return existing

    conversation = session.get(Conversation, message.conversation_id)
    if conversation is None:
        return None
    local_now = datetime.now(_business_timezone(session))
    commitment = Commitment(
        conversation_id=conversation.id,
        customer_id=conversation.customer_id,
        source_message_id=message.id,
        promise_text=message.text,
        actor=actor,
        due_at=promise_due(message.text, now=local_now),
    )
    session.add(commitment)
    # autoflush is off in this project (`app/db.py`), so without this the second
    # call in the same transaction would not see the first row in its own check
    # and the unique index would raise instead of returning the existing promise.
    session.flush()
    return commitment
