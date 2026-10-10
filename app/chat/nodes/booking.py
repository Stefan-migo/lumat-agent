"""Deterministic customer-confirmed appointment booking."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select

from app.chat.state import ConversationState
from app.db import session_scope
from app.models import Case, Conversation
from app.services import scheduling
from app.services import technician_schedule
from app.services.settings import get_hours_timezone

OFFER_TTL = timedelta(minutes=30)
MAX_INVALID_REPLIES = 1
SERVICE = "Visita técnica"
DURATION_MINUTES = 60


def _fold(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", value.casefold())
        if not unicodedata.combining(char)
    ).strip()


def _persist_offer(session, state: ConversationState, offer: dict | None) -> None:
    conversation = session.get(Conversation, state.conversation_id)
    if conversation is None:
        return
    captured = dict(conversation.captured_data or {})
    if offer is None:
        captured.pop("_booking_offer", None)
    else:
        captured["_booking_offer"] = offer
    conversation.captured_data = captured


def _offer_text(slots: list[dict]) -> str:
    return "Tengo estos horarios disponibles para la visita técnica:\n" + "\n".join(
        f"{index}. {slot['date']} {slot['time']}"
        for index, slot in enumerate(slots, 1)
    ) + "\nResponde con el número del horario que prefieres."


def _new_offer(session, state: ConversationState, now: datetime, *, attempts: int = 0) -> dict:
    case = session.scalar(
        select(Case).where(
            Case.conversation_id == state.conversation_id,
            Case.customer_id == state.customer_id,
        ).order_by(Case.id.desc()).limit(1)
    )
    if case is None:
        return {"next_step": "handoff", "escalate": True, "escalate_reason": "booking_missing_case"}
    technician_schedule.ensure_horizon(session, now)
    assignments = scheduling.open_slots_for_assignment(
        session, now=now, days=7, duration_minutes=DURATION_MINUTES, limit=3
    )
    if not assignments:
        return {"next_step": "handoff", "escalate": True, "escalate_reason": "booking_unavailable"}
    slots = [
        {"technician_id": technician_id, "date": day.isoformat(), "time": clock.isoformat()}
        for technician_id, day, clock in assignments
    ]
    offer = {"slots": slots, "created_at": now.isoformat(), "attempts": attempts}
    _persist_offer(session, state, offer)
    return {"next_step": "end", "replies": [_offer_text(slots)]}


def _resolve(text: str, slots: list[dict]) -> int | None:
    match = re.fullmatch(r"\s*(?:(?:opcion|horario)\s*)?(\d+)\s*", _fold(text))
    if match:
        index = int(match.group(1)) - 1
        return index if 0 <= index < len(slots) else None
    normalized = _fold(text)
    matches = [
        index for index, slot in enumerate(slots)
        if normalized in {
            _fold(f"{slot['date']} {slot['time']}"),
            _fold(f"{date.fromisoformat(slot['date']).strftime('%d/%m')} {slot['time'][:5]}"),
        }
    ]
    return matches[0] if len(matches) == 1 else None


def booking(state: ConversationState) -> dict:
    """Offer frozen slots or commit exactly one customer-selected slot."""
    message = state.window[-1] if state.window else {}
    text = message.get("text") or ""
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        conversation = session.get(Conversation, state.conversation_id)
        offer = dict((conversation.captured_data or {}).get("_booking_offer") or {}) if conversation else {}
        if not offer:
            return _new_offer(session, state, now)
        try:
            created_at = datetime.fromisoformat(offer["created_at"])
            if created_at.tzinfo is None or now - created_at > OFFER_TTL:
                _persist_offer(session, state, None)
                return _new_offer(session, state, now)
        except (KeyError, ValueError):
            _persist_offer(session, state, None)
            return _new_offer(session, state, now)

        slots = offer.get("slots") or []
        selected = _resolve(text, slots)
        if selected is None:
            attempts = int(offer.get("attempts", 0))
            if attempts >= MAX_INVALID_REPLIES:
                _persist_offer(session, state, None)
                return {"next_step": "handoff", "escalate": True, "escalate_reason": "booking_unclear"}
            offer["attempts"] = attempts + 1
            _persist_offer(session, state, offer)
            return {"next_step": "end", "replies": ["No pude identificar un único horario. Responde con el número de una opción."]}

        selected_slot = slots[selected]
        case = session.scalar(
            select(Case).where(
                Case.conversation_id == state.conversation_id,
                Case.customer_id == state.customer_id,
            ).order_by(Case.id.desc()).limit(1)
        )
        if case is None or conversation is None or conversation.customer_id != state.customer_id:
            _persist_offer(session, state, None)
            return {"next_step": "handoff", "escalate": True, "escalate_reason": "booking_missing_case"}
        timezone_name = get_hours_timezone(session)
        local_date = date.fromisoformat(selected_slot["date"])
        local_time = time.fromisoformat(selected_slot["time"])
        try:
            appointment = scheduling.book(
                session, service=SERVICE, customer_id=state.customer_id, case_id=case.id,
                technician_id=int(selected_slot["technician_id"]), local_date=local_date,
                local_time=local_time, timezone_name=timezone_name,
                duration_minutes=DURATION_MINUTES, actor="assistant",
            )
        except (scheduling.Unavailable, scheduling.AppointmentConflict):
            _persist_offer(session, state, None)
            return _new_offer(session, state, now)
        _persist_offer(session, state, None)
        slot_label = appointment.local_start.strftime("%d/%m/%Y a las %H:%M")
        return {
            "next_step": "summary",
            "replies": [f"Tu visita técnica quedó confirmada para el {slot_label}."],
        }
