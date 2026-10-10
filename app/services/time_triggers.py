"""Publish due occurrences for installed time-offset automation recipes."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Appointment, AppointmentStatus, AutomationInstallation, Customer,
)
from app.services.events import publish_event
from app.services.recipes import RecipeDefinition, get_recipe

try:
    from dateutil.relativedelta import relativedelta
except ImportError:
    relativedelta = None


@dataclass(frozen=True)
class DueOccurrence:
    entity_type: str
    entity_id: str
    payload: dict
    dedupe_key: str


def _add_months(value: datetime, months: int) -> datetime:
    """Add calendar months, clamping to the destination month's last day."""
    month_index = value.year * 12 + value.month - 1 + months
    year, month = divmod(month_index, 12)
    month += 1
    return value.replace(year=year, month=month, day=min(value.day, monthrange(year, month)[1]))


def _shift(value: datetime, *, days: int = 0, months: int = 0) -> datetime:
    if months and relativedelta is not None:
        return value + relativedelta(months=months)
    return _add_months(value, months) if months else value + timedelta(days=days)


def _recipient(customer: Customer, parameters: dict) -> str | None:
    value = customer.email if parameters.get("channel") == "email" else customer.phone_e164
    return value or None


def _review_due(session: Session, installation: AutomationInstallation, recipe: RecipeDefinition, now: datetime):
    parameters = recipe.validate_parameters(installation.parameters or {})
    offset = parameters["days_after"]
    lower = _shift(installation.created_at, days=-offset)
    upper = _shift(now, days=-offset)
    rows = session.execute(
        select(Appointment, Customer)
        .join(Customer, Customer.id == Appointment.customer_id)
        .where(
            Appointment.status == AppointmentStatus.COMPLETED,
            Appointment.ends_at >= lower,
            Appointment.ends_at <= upper,
        )
    )
    for appointment, customer in rows:
        recipient = _recipient(customer, parameters)
        if recipient:
            yield DueOccurrence(
                "appointment", str(appointment.id),
                {"customer_id": customer.id, "appointment_id": appointment.id, "recipient": recipient},
                f"appointment:{appointment.id}:review",
            )


def _maintenance_due(session: Session, installation: AutomationInstallation, recipe: RecipeDefinition, now: datetime):
    parameters = recipe.validate_parameters(installation.parameters or {})
    offset = parameters["months"]
    latest = (
        select(Appointment.customer_id.label("customer_id"), func.max(Appointment.ends_at).label("ends_at"))
        .where(Appointment.status == AppointmentStatus.COMPLETED)
        .group_by(Appointment.customer_id)
        .subquery()
    )
    rows = session.execute(
        select(latest.c.customer_id, latest.c.ends_at, Customer)
        .join(Customer, Customer.id == latest.c.customer_id)
        .where(latest.c.ends_at >= _shift(installation.created_at, months=-offset))
    )
    for customer_id, last_ends_at, customer in rows:
        due_at = _shift(last_ends_at, months=offset)
        recipient = _recipient(customer, parameters)
        if due_at <= now and recipient:
            yield DueOccurrence(
                "customer", str(customer_id), {"customer_id": customer_id, "recipient": recipient},
                f"customer:{customer_id}:maintenance:{last_ends_at.date().isoformat()}",
            )


_EVALUATORS = {
    "appointment_review_request": _review_due,
    "customer_maintenance": _maintenance_due,
}


def evaluate_time_triggers(session: Session, now: datetime) -> int:
    """Publish due offset occurrences; publish_event owns deduplication by key."""
    count = 0
    installations = session.scalars(
        select(AutomationInstallation).where(AutomationInstallation.enabled.is_(True))
    )
    for installation in installations:
        recipe = get_recipe(installation.recipe_id)
        if recipe is None or recipe.trigger_kind != "offset":
            continue
        evaluator = _EVALUATORS.get(installation.recipe_id)
        if evaluator is None:
            continue
        for occurrence in evaluator(session, installation, recipe, now):
            publish_event(
                session, event_type=recipe.event_type, entity_type=occurrence.entity_type,
                entity_id=occurrence.entity_id, payload=occurrence.payload,
                dedupe_key=occurrence.dedupe_key,
            )
            count += 1
    return count
