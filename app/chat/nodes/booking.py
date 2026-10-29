"""Deterministic customer-confirmed appointment booking."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select

from app.chat.nodes.replies import render_reply
from app.chat.slot_window import SlotWindow, resolve_window, window_label
from app.chat.state import ConversationState
from app.db import session_scope
from app.models import Case, Conversation, User
from app.services import scheduling
from app.services import technician_schedule
from app.services.settings import (
    get_booking_lead_minutes,
    get_hours_timezone,
    get_reply_texts,
    get_service_duration,
)
from zoneinfo import ZoneInfo

OFFER_TTL = timedelta(minutes=30)
MAX_INVALID_REPLIES = 1
# S1 (chatbot-experiencia): "más horarios" pages through a frozen offer instead of
# deriving. The universe is built once, when the offer is created, so a later page
# never drifts with the clock and never depends on bookings made by someone else.
PAGE_SIZE = 3
UNIVERSE_LIMIT = 30
# S2 (agenda-preferencia): when the requested day holds nothing, the offer moves
# forward to the nearest day that does. Bounded so a week with no coverage stays a
# handoff instead of an unbounded scan.
FALLBACK_DAYS = 7
SERVICE = "Visita técnica"
DEFAULT_DURATION_MINUTES = 60

# S1: asking for another time is a request this node can serve, not a failed
# understanding. The booking node is deterministic and never asks the model, so the
# vocabulary lives here; the list stays narrow on purpose, because anything it does
# not match still gets the clarification and then a person.
_MORE_SLOTS_MARKERS = (
    "mas horario", "otros horario", "otro horario", "otra hora", "otras horas",
    "mas opcion", "otras opciones", "siguientes horarios",
    "otro dia", "otros dias", "otra fecha", "otras fechas",
    "no puedo en esos", "no puedo en esas", "no me sirve", "no me sirven",
    "ninguno me sirve", "ninguna me sirve",
)


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


def _options(slots: list[dict]) -> str:
    return "\n".join(
        f"{index}. {datetime.combine(date.fromisoformat(slot['date']), time.fromisoformat(slot['time'])):%d/%m/%Y a las %H:%M}"
        for index, slot in enumerate(slots, 1)
    )


def _offer_text(slots: list[dict], texts: dict[str, str]) -> str:
    return render_reply(texts, "booking_offer", opciones=_options(slots))


def _requests_more_slots(text: str) -> bool:
    normalized = _fold(text)
    return any(marker in normalized for marker in _MORE_SLOTS_MARKERS)


def _slot_entries(assignments: list[tuple[int, date, time]]) -> list[dict]:
    return [
        {"technician_id": technician_id, "date": day.isoformat(), "time": clock.isoformat()}
        for technician_id, day, clock in assignments
    ]


def local_today(session, now: datetime) -> date:
    """The business-local date: every window the customer speaks is local."""

    return now.astimezone(ZoneInfo(get_hours_timezone(session))).date()


def _requested_window(session, state: ConversationState, now: datetime) -> SlotWindow | None:
    """S1: the day and franja the customer already stated during capture."""

    conversation = session.get(Conversation, state.conversation_id)
    if conversation is None:
        return None
    availability = (conversation.captured_data or {}).get("availability") or ""
    return resolve_window(str(availability), today=local_today(session, now))


def _search_slots(
    session,
    now: datetime,
    today: date,
    duration: int,
    window: SlotWindow | None,
    limit: int = UNIVERSE_LIMIT,
) -> list[tuple[int, date, time]]:
    """Slots for a window, widening the day count when the day sits past it.

    A named day is reachable by definition: the request itself extends the search,
    so "para el viernes 30" is answered instead of silently ignored.
    """

    days = 7
    if window is not None and window.day is not None:
        days = max(days, (window.day - today).days + 1)
    return scheduling.open_slots_for_assignment(
        session, now=now, days=days, duration_minutes=duration, limit=limit,
        # S1: a visit offered for "right now" cannot be staffed.
        lead_minutes=get_booking_lead_minutes(session),
        window=window,
    )


def slots_for_window(
    session,
    *,
    now: datetime,
    duration_minutes: int,
    window: SlotWindow | None,
    limit: int = UNIVERSE_LIMIT,
) -> tuple[list[tuple[int, date, time]], bool]:
    """Slots for a requested window, moving forward when that window holds nothing.

    S2 (agenda-preferencia): moving *forward* is the rule — handing back a day the
    customer already ruled out is worse than saying the day is full. The same
    widening covers a franja that leaves nothing, so a preference never dead-ends.

    Returns the assignments and whether the fallback produced them, because the
    reply differs: a widened offer has to say what was asked and is unavailable.
    """

    today = local_today(session, now)
    assignments = _search_slots(session, now, today, duration_minutes, window, limit)
    if assignments or window is None:
        return assignments, False
    if window.day is not None:
        for offset in range(1, FALLBACK_DAYS + 1):
            day = window.day + timedelta(days=offset)
            assignments = _search_slots(
                session, now, today, duration_minutes, SlotWindow(day=day), limit
            )
            if assignments:
                return assignments, True
        return [], False
    widened = _search_slots(session, now, today, duration_minutes, None, limit)
    return widened, bool(widened)


def _new_offer(
    session,
    state: ConversationState,
    now: datetime,
    texts: dict[str, str],
    *,
    attempts: int = 0,
    window: SlotWindow | None = None,
    unchanged_against: dict | None = None,
) -> dict:
    case = session.scalar(
        select(Case).where(
            Case.conversation_id == state.conversation_id,
            Case.customer_id == state.customer_id,
        ).order_by(Case.id.desc()).limit(1)
    )
    if case is None:
        return {"next_step": "handoff", "escalate": True, "escalate_reason": "booking_missing_case"}
    if window is None:
        window = _requested_window(session, state, now)
    duration = get_service_duration(session, case.service, default=DEFAULT_DURATION_MINUTES)
    technician_schedule.ensure_horizon(session, now)
    assignments, widened = slots_for_window(
        session, now=now, duration_minutes=duration, window=window
    )
    if not assignments:
        return {"next_step": "handoff", "escalate": True, "escalate_reason": "booking_unavailable"}
    universe = _slot_entries(assignments)
    slots = universe[:PAGE_SIZE]
    # S10: a preference the parser cannot read rebuilds the offer for the day it did
    # read, which can be the very page already on screen. Printing it again is the
    # loop production #23 sat in for four turns, so the caller is told instead.
    if unchanged_against is not None and slots == (unchanged_against.get("slots") or []):
        return {"next_step": "end", "_unchanged_offer": True}
    offer = {
        "slots": slots, "universe": universe, "shown": len(slots),
        "created_at": now.isoformat(), "attempts": attempts,
    }
    _persist_offer(session, state, offer)
    if widened:
        return {"next_step": "end", "replies": [
            render_reply(
                texts, "booking_window_unavailable",
                momento=window_label(window), opciones=_options(slots),
            )
        ]}
    return {"next_step": "end", "replies": [_offer_text(slots, texts)]}


def _invalid_offer(
    session, state: ConversationState, offer: dict, texts: dict[str, str], attempts: int
) -> dict:
    """Count a preference the offer could not serve; the limit hands off.

    S10: the counter used to restart every time the offer was rebuilt, so
    `MAX_INVALID_REPLIES` was unreachable and the customer could be shown the same
    list indefinitely.
    """
    if attempts > MAX_INVALID_REPLIES:
        _persist_offer(session, state, None)
        return {"next_step": "handoff", "escalate": True, "escalate_reason": "booking_unclear"}
    offer = {**offer, "attempts": attempts}
    _persist_offer(session, state, offer)
    return {"next_step": "end", "replies": [render_reply(texts, "booking_unclear")]}


def _more_slots(session, state: ConversationState, offer: dict, texts: dict[str, str]) -> dict:
    """Serve the next page of the frozen offer, or escalate when nothing is left.

    The page keeps the numbering the customer replies with, and when it no longer
    falls on the same day the answered offer was for, the reply says so instead of
    silently jumping to another day.
    """
    current = offer.get("slots") or []
    shown = int(offer.get("shown", len(current)))
    page = (offer.get("universe") or [])[shown:shown + PAGE_SIZE]
    if not page:
        _persist_offer(session, state, None)
        return {"next_step": "handoff", "escalate": True, "escalate_reason": "booking_unavailable"}
    offer = {**offer, "slots": page, "shown": shown + len(page), "attempts": 0}
    _persist_offer(session, state, offer)
    if current and date.fromisoformat(page[0]["date"]) > date.fromisoformat(current[-1]["date"]):
        return {"next_step": "end", "replies": [
            render_reply(texts, "booking_no_more_today", opciones=_options(page))
        ]}
    return {"next_step": "end", "replies": [_offer_text(page, texts)]}


def is_offer_answer(text: str, slots: list[dict], *, today: date) -> bool:
    """Whether ``text`` answers an open offer: a choice, a day, or a page request.

    S3 (agenda-preferencia): the handoff gate and this node must agree on what
    counts as answering the offer. Before this, "no me sirve" was a page request
    here and a complaint in the gate, and the gate ran first.
    """

    if _resolve(text, slots) is not None:
        return True
    if resolve_window(text, today=today) is not None:
        return True
    return _requests_more_slots(text)


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


# S1 (chatbot-experiencia): the confirmation names the technician that will attend.
# A technician without a loaded name must not leave a hole in the sentence.
TEAM_FALLBACK = "nuestro equipo técnico"


def _technician_name(session, technician_id: int) -> str:
    technician = session.get(User, technician_id)
    name = technician.name.strip() if technician and technician.name else ""
    return name or TEAM_FALLBACK


def booking(state: ConversationState) -> dict:
    """Offer frozen slots or commit exactly one customer-selected slot."""
    message = state.window[-1] if state.window else {}
    text = message.get("text") or ""
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        texts = get_reply_texts(session)
        conversation = session.get(Conversation, state.conversation_id)
        offer = dict((conversation.captured_data or {}).get("_booking_offer") or {}) if conversation else {}
        if not offer:
            return _new_offer(session, state, now, texts)
        try:
            created_at = datetime.fromisoformat(offer["created_at"])
            if created_at.tzinfo is None or now - created_at > OFFER_TTL:
                _persist_offer(session, state, None)
                return _new_offer(session, state, now, texts)
        except (KeyError, ValueError):
            _persist_offer(session, state, None)
            return _new_offer(session, state, now, texts)

        slots = offer.get("slots") or []
        attempts = int(offer.get("attempts", 0))
        selected = _resolve(text, slots)
        if selected is None:
            # S1/S4: naming a day — or asking whether one has room — is a request
            # this node can serve, so it rebuilds the offer for that day instead of
            # spending the single clarification the handoff sits behind.
            requested = resolve_window(text, today=local_today(session, now))
            if requested is not None:
                rebuilt = _new_offer(
                    session, state, now, texts,
                    window=requested, attempts=attempts + 1, unchanged_against=offer,
                )
                if rebuilt.pop("_unchanged_offer", False):
                    return _invalid_offer(session, state, offer, texts, attempts + 1)
                return rebuilt
            if _requests_more_slots(text):
                return _more_slots(session, state, offer, texts)
            if attempts >= MAX_INVALID_REPLIES:
                _persist_offer(session, state, None)
                return {"next_step": "handoff", "escalate": True, "escalate_reason": "booking_unclear"}
            offer["attempts"] = attempts + 1
            _persist_offer(session, state, offer)
            return {"next_step": "end", "replies": [render_reply(texts, "booking_unclear")]}

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
        duration = get_service_duration(session, case.service, default=DEFAULT_DURATION_MINUTES)
        timezone_name = get_hours_timezone(session)
        local_date = date.fromisoformat(selected_slot["date"])
        local_time = time.fromisoformat(selected_slot["time"])
        try:
            appointment = scheduling.book(
                session, service=SERVICE, customer_id=state.customer_id, case_id=case.id,
                technician_id=int(selected_slot["technician_id"]), local_date=local_date,
                local_time=local_time, timezone_name=timezone_name,
                duration_minutes=duration, actor="assistant",
            )
        except (scheduling.Unavailable, scheduling.AppointmentConflict):
            _persist_offer(session, state, None)
            return _new_offer(session, state, now, texts)
        _persist_offer(session, state, None)
        slot_label = appointment.local_start.strftime("%d/%m/%Y a las %H:%M")
        technician_name = _technician_name(session, appointment.technician_id)
        return {
            "next_step": "summary",
            "replies": [
                render_reply(
                    texts, "booking_confirmed", fecha=slot_label, tecnico=technician_name
                )
            ],
        }
