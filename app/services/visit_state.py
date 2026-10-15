"""Technician visit-state axis (S5/S6).

`en_route` and `arrived` describe where the technician is relative to the visit.
They are an axis orthogonal to `AppointmentStatus` and are never folded into that
enum: `AppointmentStatus` owns the visit lifecycle, this owns the field position.

Transitions are forward-only (an earlier state can never be re-entered), but
re-marking the CURRENT state is allowed — that is what a resend is; the 5-minute
resend cooldown is enforced by the caller. Every recorded transition writes one
append-only `audit_log` entry and never touches `AppointmentHistory`, whose
`to_status` is NOT NULL on the status enum.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Appointment, AppointmentStatus, TechnicianVisitState
from app.services.audit import record_audit

# Availability windows (S6): `en_route` from T-60 min, `arrived` from T-15 min.
# Both close at the visit's `ends_at`, or earlier if the visit is closed.
EN_ROUTE_LEAD = timedelta(minutes=60)
ARRIVED_LEAD = timedelta(minutes=15)

_LEAD = {
    TechnicianVisitState.EN_ROUTE: EN_ROUTE_LEAD,
    TechnicianVisitState.ARRIVED: ARRIVED_LEAD,
}

# Position on the axis; a transition may stay or move forward, never backwards.
_ORDER = {
    TechnicianVisitState.EN_ROUTE: 1,
    TechnicianVisitState.ARRIVED: 2,
}


class VisitStateUnavailable(ValueError):
    """The transition is outside its window, the visit is closed, or it would move backwards."""


def opens_at(appointment: Appointment, state: TechnicianVisitState) -> datetime:
    """When `state` becomes available (S6)."""
    return appointment.starts_at - _LEAD[state]


def is_available(appointment: Appointment, state: TechnicianVisitState, now: datetime | None = None) -> bool:
    """Whether `state` can be recorded right now (S6).

    The visit must still be booked, `now` must fall inside the state's window
    (`opens_at` .. `ends_at`), and the axis must not have moved past `state`."""
    moment = now or datetime.now(timezone.utc)
    if appointment.status is not AppointmentStatus.BOOKED:
        return False
    if moment >= appointment.ends_at:
        return False
    if moment < opens_at(appointment, state):
        return False
    current = appointment.technician_state
    return current is None or _ORDER[current] <= _ORDER[state]


def mark(
    session: Session,
    appointment: Appointment,
    *,
    state: TechnicianVisitState,
    actor: str,
    now: datetime | None = None,
) -> Appointment:
    """Record the technician's field state on the visit and audit it (S5/S6).

    Raises `VisitStateUnavailable` when the window is closed or the transition
    would move backwards; nothing is written in that case."""
    moment = now or datetime.now(timezone.utc)
    if not is_available(appointment, state, moment):
        raise VisitStateUnavailable(f"{state.value} is not available for this visit")
    previous = appointment.technician_state
    appointment.technician_state = state
    appointment.technician_state_at = moment
    session.flush()
    record_audit(
        session,
        actor=actor,
        action=f"appointment.{state.value}",
        entity="appointment",
        entity_id=str(appointment.id),
        before={"technician_state": previous.value if previous is not None else None},
        after={"technician_state": state.value, "technician_state_at": moment.isoformat()},
    )
    return appointment
