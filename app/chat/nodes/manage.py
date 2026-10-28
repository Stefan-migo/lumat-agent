"""Deterministic customer-confirmed appointment management."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select

from app.chat.state import ConversationState
from app.chat.nodes.booking import _resolve, local_today, slots_for_window
from app.chat.slot_window import resolve_window, window_label
from app.chat.nodes.replies import render_reply
from app.db import session_scope
from app.models import Appointment, AppointmentStatus, Conversation
from app.services import scheduling
from app.services.settings import get_hours_timezone, get_reply_texts

OFFER_TTL = timedelta(minutes=30)
MAX_INVALID_REPLIES = 1
# A reschedule shows one page and no frozen universe: the customer is moving an
# existing visit, so three options are the offer, not the first page of many.
RESCHEDULE_SLOTS = 3


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
        captured.pop("_manage_offer", None)
    else:
        captured["_manage_offer"] = offer
    conversation.captured_data = captured


def _handoff(session, state: ConversationState, reason: str) -> dict:
    _persist_offer(session, state, None)
    return {"next_step": "handoff", "escalate": True, "escalate_reason": reason}


def _appointment_query(customer_id: int, now: datetime):
    return (
        select(Appointment)
        .where(
            Appointment.customer_id == customer_id,
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.starts_at > now,
        )
        .order_by(Appointment.starts_at)
    )


def _appointment_label(appointment: Appointment) -> str:
    return f"{appointment.local_start.strftime('%d/%m/%Y a las %H:%M')} — {appointment.service}"


def _start_offer(
    session, state: ConversationState, now: datetime, mode: str, texts: dict[str, str]
) -> dict:
    text = state.window[-1].get("text") or "" if state.window else ""
    appointments = session.scalars(_appointment_query(state.customer_id, now)).all()
    if not appointments:
        _persist_offer(session, state, None)
        action = "reagendar" if mode == "reschedule" else "cancelar"
        return {"next_step": "end", "replies": [render_reply(texts, "manage_no_visits", accion=action)]}

    shown = appointments[:3]
    if len(appointments) == 1:
        appointment = shown[0]
        offer = {"mode": mode, "appointment_id": appointment.id, "phase": "confirm", "attempts": 0, "created_at": now.isoformat()}
        prompt = render_reply(
            texts, "manage_confirm_cancel", visita=_appointment_label(appointment)
        )
        if mode == "reschedule":
            return _new_reschedule_offer(session, state, appointment, now, texts, text=text)
    else:
        offer = {"mode": mode, "appointment_ids": [item.id for item in shown], "phase": "select", "attempts": 0, "created_at": now.isoformat()}
        action = "reagendar" if mode == "reschedule" else "cancelar"
        prompt = render_reply(
            texts,
            "manage_select",
            accion=action,
            opciones="\n".join(
                f"{index}. {_appointment_label(appointment)}"
                for index, appointment in enumerate(shown, 1)
            ),
        )
    _persist_offer(session, state, offer)
    return {"next_step": "end", "replies": [prompt]}


def _new_reschedule_offer(
    session,
    state: ConversationState,
    appointment: Appointment,
    now: datetime,
    texts: dict[str, str],
    *,
    attempts: int = 0,
    text: str = "",
) -> dict:
    window = resolve_window(text, today=local_today(session, now))
    assignments, widened = slots_for_window(
        session,
        now=now,
        duration_minutes=appointment.duration_minutes,
        window=window,
        limit=RESCHEDULE_SLOTS,
    )
    if not assignments:
        return _handoff(session, state, "manage_reschedule_unavailable")
    slots = [
        {"technician_id": technician_id, "date": day.isoformat(), "time": clock.isoformat()}
        for technician_id, day, clock in assignments
    ]
    offer = {
        "mode": "reschedule", "appointment_id": appointment.id, "phase": "slots",
        "slots": slots, "created_at": now.isoformat(), "attempts": attempts,
    }
    _persist_offer(session, state, offer)
    opciones = "\n".join(
        f"{index}. {datetime.combine(date.fromisoformat(slot['date']), time.fromisoformat(slot['time'])):%d/%m/%Y a las %H:%M}"
        for index, slot in enumerate(slots, 1)
    )
    if widened:
        prompt = render_reply(
            texts, "booking_window_unavailable",
            momento=window_label(window), opciones=opciones,
        )
    else:
        prompt = render_reply(texts, "manage_slots_offer", opciones=opciones)
    return {"next_step": "end", "replies": [prompt]}


def _invalid(session, state: ConversationState, offer: dict, prompt: str, reason: str) -> dict:
    attempts = int(offer.get("attempts", 0))
    if attempts >= MAX_INVALID_REPLIES:
        return _handoff(session, state, reason)
    offer["attempts"] = attempts + 1
    _persist_offer(session, state, offer)
    return {"next_step": "end", "replies": [prompt]}


def manage(state: ConversationState) -> dict:
    """Cancel or reschedule an upcoming visit using a persisted customer offer."""
    text = state.window[-1].get("text") or "" if state.window else ""
    now = datetime.now(timezone.utc)
    classified_mode = "reschedule" if state.intent == "reagendar_visita" else "cancel"
    with session_scope() as session:
        texts = get_reply_texts(session)
        conversation = session.get(Conversation, state.conversation_id)
        offer = dict((conversation.captured_data or {}).get("_manage_offer") or {}) if conversation else {}
        mode = offer.get("mode") or classified_mode
        if not offer:
            return _start_offer(session, state, now, mode, texts)
        try:
            created_at = datetime.fromisoformat(offer["created_at"])
            if created_at.tzinfo is None or now - created_at > OFFER_TTL:
                _persist_offer(session, state, None)
                return {"next_step": "end", "replies": [render_reply(texts, "manage_expired")]}
        except (KeyError, ValueError):
            _persist_offer(session, state, None)
            return {"next_step": "end", "replies": [render_reply(texts, "manage_expired")]}

        if offer.get("mode") != mode:
            return _handoff(session, state, "manage_invalid_mode")
        if offer.get("phase") == "select":
            match = re.fullmatch(r"\s*(\d+)\s*", _fold(text))
            index = int(match.group(1)) - 1 if match else -1
            ids = offer.get("appointment_ids") or []
            if not 0 <= index < len(ids):
                return _invalid(
                    session,
                    state,
                    offer,
                    render_reply(texts, "manage_appointment_unclear"),
                    "manage_unclear",
                )
            offer = {"mode": mode, "appointment_id": ids[index], "phase": "confirm", "attempts": 0, "created_at": offer["created_at"]}
            appointment = session.get(Appointment, ids[index])
            if appointment is None or appointment.customer_id != state.customer_id:
                return _handoff(session, state, "manage_appointment_unavailable")
            if mode == "reschedule":
                return _new_reschedule_offer(session, state, appointment, now, texts, text=text)
            _persist_offer(session, state, offer)
            return {
                "next_step": "end",
                "replies": [
                    render_reply(
                        texts,
                        "manage_confirm_cancel",
                        visita=_appointment_label(appointment),
                    )
                ],
            }

        if mode == "reschedule" and offer.get("phase") == "slots":
            if " ".join(re.sub(r"[^\w\s]", " ", _fold(text)).split()) in {"no", "no gracias", "mejor no"}:
                _persist_offer(session, state, None)
                return {"next_step": "end", "replies": [render_reply(texts, "manage_kept")]}
            slots = offer.get("slots") or []
            selected = _resolve(text, slots)
            if selected is None:
                return _invalid(
                    session,
                    state,
                    offer,
                    render_reply(texts, "manage_slots_unclear"),
                    "manage_unclear",
                )
            appointment = session.get(Appointment, offer.get("appointment_id"))
            if (appointment is None or appointment.customer_id != state.customer_id
                    or appointment.status is not AppointmentStatus.BOOKED
                    or appointment.starts_at <= datetime.now(timezone.utc)):
                _persist_offer(session, state, None)
                return {
                    "next_step": "end",
                    "replies": [render_reply(texts, "manage_reschedule_unavailable")],
                }
            slot = slots[selected]
            timezone_name = get_hours_timezone(session)
            try:
                scheduling.reschedule(
                    session, appointment, local_date=date.fromisoformat(slot["date"]),
                    local_time=time.fromisoformat(slot["time"]), timezone_name=timezone_name,
                    duration_minutes=appointment.duration_minutes,
                    technician_id=int(slot["technician_id"]), actor="assistant",
                )
            except (scheduling.AppointmentConflict, scheduling.Unavailable):
                return _new_reschedule_offer(session, state, appointment, now, texts)
            _persist_offer(session, state, None)
            return {
                "next_step": "summary",
                "replies": [
                    render_reply(
                        texts,
                        "manage_rescheduled",
                        fecha=appointment.local_start.strftime("%d/%m/%Y a las %H:%M"),
                    )
                ],
            }

        answer = " ".join(re.sub(r"[^\w\s]", " ", _fold(text)).split())
        affirmative = answer in {"si", "confirmo", "confirmar", "acepto", "yes", "si confirmo", "confirmo si"}
        negative = answer in {"no", "nope", "negativo", "no confirmo", "no gracias"}
        if not affirmative and not negative:
            return _invalid(
                session,
                state,
                offer,
                render_reply(texts, "manage_cancel_prompt"),
                "manage_unclear",
            )
        if negative:
            _persist_offer(session, state, None)
            return {"next_step": "end", "replies": [render_reply(texts, "manage_kept")]}

        appointment = session.get(Appointment, offer.get("appointment_id"))
        if (
            appointment is None
            or appointment.customer_id != state.customer_id
            or appointment.status is not AppointmentStatus.BOOKED
            or appointment.starts_at <= datetime.now(timezone.utc)
        ):
            _persist_offer(session, state, None)
            return {
                "next_step": "end",
                "replies": [render_reply(texts, "manage_cancel_unavailable")],
            }
        scheduling.cancel(session, appointment, actor="assistant")
        _persist_offer(session, state, None)
        return {
            "next_step": "summary",
            "replies": [
                render_reply(texts, "manage_cancelled", visita=_appointment_label(appointment))
            ],
        }
