"""Deterministic customer-confirmed appointment management."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.chat.state import ConversationState
from app.db import session_scope
from app.models import Appointment, AppointmentStatus, Conversation
from app.services import scheduling

OFFER_TTL = timedelta(minutes=30)
MAX_INVALID_REPLIES = 1


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


def _start_offer(session, state: ConversationState, now: datetime) -> dict:
    appointments = session.scalars(_appointment_query(state.customer_id, now)).all()
    if not appointments:
        _persist_offer(session, state, None)
        return {"next_step": "end", "replies": ["No tienes visitas próximas para cancelar."]}

    shown = appointments[:3]
    if len(appointments) == 1:
        appointment = shown[0]
        offer = {"mode": "cancel", "appointment_id": appointment.id, "phase": "confirm", "attempts": 0, "created_at": now.isoformat()}
        prompt = f"Tienes una visita el {_appointment_label(appointment)}. ¿Confirmas que quieres cancelarla? Responde sí o no."
    else:
        offer = {"mode": "cancel", "appointment_ids": [item.id for item in shown], "phase": "select", "attempts": 0, "created_at": now.isoformat()}
        prompt = "¿Cuál visita quieres cancelar?\n" + "\n".join(
            f"{index}. {_appointment_label(appointment)}" for index, appointment in enumerate(shown, 1)
        ) + "\nResponde con el número de la visita."
    _persist_offer(session, state, offer)
    return {"next_step": "end", "replies": [prompt]}


def _invalid(session, state: ConversationState, offer: dict, prompt: str, reason: str) -> dict:
    attempts = int(offer.get("attempts", 0))
    if attempts >= MAX_INVALID_REPLIES:
        return _handoff(session, state, reason)
    offer["attempts"] = attempts + 1
    _persist_offer(session, state, offer)
    return {"next_step": "end", "replies": [prompt]}


def manage(state: ConversationState) -> dict:
    """Offer an upcoming visit and cancel only after explicit confirmation."""
    text = state.window[-1].get("text") or "" if state.window else ""
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        conversation = session.get(Conversation, state.conversation_id)
        offer = dict((conversation.captured_data or {}).get("_manage_offer") or {}) if conversation else {}
        if not offer:
            return _start_offer(session, state, now)
        try:
            created_at = datetime.fromisoformat(offer["created_at"])
            if created_at.tzinfo is None or now - created_at > OFFER_TTL:
                _persist_offer(session, state, None)
                return {"next_step": "end", "replies": ["La solicitud de cancelación venció. Si aún necesitas cancelar, vuelve a escribirnos."]}
        except (KeyError, ValueError):
            _persist_offer(session, state, None)
            return {"next_step": "end", "replies": ["La solicitud de cancelación venció. Si aún necesitas cancelar, vuelve a escribirnos."]}

        if offer.get("mode") != "cancel":
            return _handoff(session, state, "manage_invalid_mode")
        if offer.get("phase") == "select":
            match = re.fullmatch(r"\s*(\d+)\s*", _fold(text))
            index = int(match.group(1)) - 1 if match else -1
            ids = offer.get("appointment_ids") or []
            if not 0 <= index < len(ids):
                return _invalid(session, state, offer, "No pude identificar una visita. Responde con el número de una opción.", "manage_unclear")
            offer = {"mode": "cancel", "appointment_id": ids[index], "phase": "confirm", "attempts": 0, "created_at": offer["created_at"]}
            appointment = session.get(Appointment, ids[index])
            if appointment is None or appointment.customer_id != state.customer_id:
                return _handoff(session, state, "manage_appointment_unavailable")
            _persist_offer(session, state, offer)
            return {"next_step": "end", "replies": [f"Tienes una visita el {_appointment_label(appointment)}. ¿Confirmas que quieres cancelarla? Responde sí o no."]}

        answer = " ".join(re.sub(r"[^\w\s]", " ", _fold(text)).split())
        affirmative = answer in {"si", "confirmo", "confirmar", "acepto", "yes", "si confirmo", "confirmo si"}
        negative = answer in {"no", "nope", "negativo", "no confirmo", "no gracias"}
        if not affirmative and not negative:
            return _invalid(session, state, offer, "Responde sí para confirmar la cancelación o no para conservar la visita.", "manage_unclear")
        if negative:
            _persist_offer(session, state, None)
            return {"next_step": "end", "replies": ["De acuerdo, mantendremos tu visita agendada."]}

        appointment = session.get(Appointment, offer.get("appointment_id"))
        if (
            appointment is None
            or appointment.customer_id != state.customer_id
            or appointment.status is not AppointmentStatus.BOOKED
            or appointment.starts_at <= datetime.now(timezone.utc)
        ):
            _persist_offer(session, state, None)
            return {"next_step": "end", "replies": ["No puedo cancelar esta visita porque ya no está disponible para cancelación; su horario pudo haber comenzado o cambiado."]}
        scheduling.cancel(session, appointment, actor="assistant")
        _persist_offer(session, state, None)
        return {"next_step": "summary", "replies": [f"Tu visita del {_appointment_label(appointment)} quedó cancelada."]}
