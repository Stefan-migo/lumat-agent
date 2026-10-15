"""Technician field quick-actions: record the visit state and notify the customer (WU6; S7/S8).

`app.services.visit_state` owns the pure axis (S5/S6). This module owns the
customer-facing half of a quick action:

- the 5-minute resend cooldown per (appointment, action), read from the last
  matching `audit_log` event of that action (S7) — no new table, no new column;
- the Meta business-initiated template send for the state (S8); the customer
  phone is resolved here, server-side, and never returned to the frontend.

Transition, audit row and send are one transaction: a delivery failure rolls
the whole action back, so the technician can retry immediately. The template
body contract is `{{1}}` customer name, `{{2}}` technician name, `{{3}}` visit
date, `{{4}}` visit time — the two Meta templates themselves are external (EXT).

The route that calls this acquires the appointment row `FOR UPDATE` first, so
two rapid clicks serialize on the cooldown read. The operation's
`idempotency_key` (`appointment:<id>:visit_state:<state>:<cooldown bucket>`)
makes a replayed send a no-op: a bucket is 5 minutes wide, so any resend the
cooldown allows (at least 5 minutes on) always lands in a later bucket.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Appointment, AuditLog, Customer, TechnicianVisitState, User
from app.services import notify, visit_state
from app.services.notifications import create_operation, process_operation
from app.services.settings import get_setting

RESEND_COOLDOWN = timedelta(minutes=5)

_TEMPLATE_SETTING_KEYS = {
    TechnicianVisitState.EN_ROUTE: "notify.en_route_template_name",
    TechnicianVisitState.ARRIVED: "notify.arrived_template_name",
}
_DEFAULT_TEMPLATE_NAMES = {
    TechnicianVisitState.EN_ROUTE: "en_route",
    TechnicianVisitState.ARRIVED: "arrived",
}


class ResendCooldown(ValueError):
    """The same quick action was recorded inside its cooldown window (S7)."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(f"a message was sent less than {RESEND_COOLDOWN} ago")
        self.retry_after_seconds = retry_after_seconds


class VisitNotificationFailed(RuntimeError):
    """The customer template could not be delivered; the action was not applied."""


def _audit_action(state: TechnicianVisitState) -> str:
    return f"appointment.{state.value}"


def last_recorded_at(
    session: Session, appointment_id: int, state: TechnicianVisitState
) -> datetime | None:
    """When this quick action was last recorded for the appointment (S7)."""
    return session.scalar(
        select(AuditLog.created_at)
        .where(
            AuditLog.action == _audit_action(state),
            AuditLog.entity == "appointment",
            AuditLog.entity_id == str(appointment_id),
        )
        .order_by(AuditLog.id.desc())
        .limit(1)
    )


def cooldown_remaining(
    session: Session,
    appointment_id: int,
    state: TechnicianVisitState,
    *,
    now: datetime | None = None,
) -> timedelta:
    """How long until `state` may be recorded again for the appointment (S7)."""
    moment = now or datetime.now(timezone.utc)
    last = last_recorded_at(session, appointment_id, state)
    if last is None:
        return timedelta(0)
    remaining = last + RESEND_COOLDOWN - moment
    return remaining if remaining > timedelta(0) else timedelta(0)


def resend_available_at(
    session: Session,
    appointment_id: int,
    state: TechnicianVisitState,
    *,
    now: datetime | None = None,
) -> datetime | None:
    """When this quick action unlocks again, or `None` when it is not cooling down (S7).

    Same audit-row read as the guard, exposed so a read can render the countdown
    without the frontend re-deriving the cooldown."""
    moment = now or datetime.now(timezone.utc)
    remaining = cooldown_remaining(session, appointment_id, state, now=moment)
    return moment + remaining if remaining > timedelta(0) else None


def notify_customer(
    session: Session,
    appointment: Appointment,
    *,
    state: TechnicianVisitState,
    actor: str,
    now: datetime | None = None,
) -> Appointment:
    """Record the visit state and send the customer template (S5-S8).

    Raises `ResendCooldown` inside the cooldown window, and
    `visit_state.VisitStateUnavailable` when the transition is outside its
    window or moves backwards; both leave nothing written.
    """
    moment = now or datetime.now(timezone.utc)
    remaining = cooldown_remaining(session, appointment.id, state, now=moment)
    if remaining > timedelta(0):
        raise ResendCooldown(math.ceil(remaining.total_seconds()))

    customer = session.get(Customer, appointment.customer_id)
    if customer is None or not customer.phone_e164:
        raise VisitNotificationFailed("appointment has no reachable customer")

    visit_state.mark(session, appointment, state=state, actor=actor, now=moment)
    _send_state_template(session, appointment, customer, state, now=moment)
    return appointment


def _send_state_template(
    session: Session,
    appointment: Appointment,
    customer: Customer,
    state: TechnicianVisitState,
    *,
    now: datetime,
) -> None:
    """Send the business-initiated WhatsApp template for the state (S8).

    The recipient is `customer.phone_e164`, resolved here and never returned.
    `{{2}}` is the technician's display name — the customer is about to receive
    a stranger at their door — with the login username as the fallback.
    """
    template_name = get_setting(
        session, _TEMPLATE_SETTING_KEYS[state], default=_DEFAULT_TEMPLATE_NAMES[state]
    )
    technician = session.get(User, appointment.technician_id)
    if technician is None:
        raise VisitNotificationFailed("appointment has no technician")
    params = [
        customer.name,
        technician.name or technician.username,
        appointment.local_start.strftime("%d/%m/%Y"),
        appointment.local_start.strftime("%H:%M"),
    ]
    bucket = int(now.timestamp() // RESEND_COOLDOWN.total_seconds())
    operation = create_operation(
        session,
        recipient=customer.phone_e164,
        channel="whatsapp",
        content=f"visit_state:{state.value}",
        source_entity="appointment",
        source_id=str(appointment.id),
        idempotency_key=f"appointment:{appointment.id}:visit_state:{state.value}:{bucket}",
    )
    if operation.status == "sent":
        return  # replayed send: the operation for this cooldown window already went out
    holder: dict = {}
    delivered = process_operation(
        session,
        operation.id,
        deliver=lambda recipient, _content: holder.setdefault(
            "wamid", notify.send_template(recipient, params, template_name=template_name)
        ),
    )
    if not delivered:
        raise VisitNotificationFailed(operation.error or "visit state notification failed")
