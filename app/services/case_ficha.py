"""Case ficha — the deterministic memory of the case (Fase 3, S1/S3).

Measured cause (D1, `odd/analysis/lumatdata/03-defectos-y-mejoras.md`): the
transcript window the model sees is six messages (`state.conversation_transcript`),
and 23 of the 34 real conversations exceed 90 messages — by turn 500 the bot has
no way to know which equipment was intervened in turn 12. Raising the window is
not the fix: it is correct for tone, and a 700-message transcript does not fit
the prompt. The fix is one bounded, structured block rebuilt from the database on
every turn: which equipment, at which property, what was intervened and when,
what is still pending, which warranty runs.

Two rules make this block trustworthy where a summary is not:

- **Deterministic.** No model call, no free text: every line is read from a row.
  The same rows always produce the same text, so a wrong line is a data defect
  and not a generation defect.
- **Bounded.** `FICHA_MAX_CHARS` is a hard ceiling, enforced by construction and
  by a final cut, because this block is injected into the prompt on every
  message (`respond` runs per message).

S3: eight of the 34 real properties belong to someone else (a tenant writing
about the owner's house, a broker, a referral), so a work done at another
address is rendered with that address and marked as another property. The
anchor is the property the work happened at, never the customer's current ficha.

The warranty window is the one published in `docs/kb/lumat-garantias-pagos.md`
and only for the services that published one; a service without a warranty gets
no window, because inventing one is exactly the money defect D7 is about.
"""

from __future__ import annotations

import unicodedata
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Appointment, AppointmentStatus, Case, Customer, CustomerEquipment
from app.services.cases import case_is_open

# S1: the hard ceiling. `respond` injects this on every message, so the block
# that survives must fit beside the transcript, the tariff and the KB chunks.
FICHA_MAX_CHARS = 1500

# Bounded sections: a customer with 40 cases still gets the recent ones first.
MAX_EQUIPMENT_LINES = 3
MAX_WORK_LINES = 8

DEFAULT_TIMEZONE = "America/Santiago"

# S1/D3: published warranties (`docs/kb/lumat-garantias-pagos.md`):
# maintenance of calefont/caldera, one year or until the next maintenance; red
# wash, six months. Keyed by the service family, matched on folded text.
WARRANTY_MONTHS: tuple[tuple[int, tuple[tuple[str, ...], ...]], ...] = (
    (12, (("mantencion", "calefont"), ("mantencion", "calefon"), ("mantencion", "caldera"))),
    (6, (("lavado", "red"),)),
)

WARRANTY_NOTE = {
    12: "1 año o hasta la próxima mantención",
    6: "6 meses",
}


def _fold(text: str | None) -> str:
    """Case-fold and strip accents, the same normalisation the gates use."""
    decomposed = unicodedata.normalize("NFKD", (text or "").casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _clip(value: str | None, limit: int) -> str:
    """Bound one free-text field so no single row can own the whole ficha."""
    text = " ".join((value or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


# Per-field ceilings. `customer_equipment.details` and `customers.address` are
# TEXT and come from the customer's own words, so the aggregate 1.500-character
# ceiling alone would let one row crowd out the work history.
MAX_ADDRESS_CHARS = 120
MAX_EQUIPMENT_DETAIL_CHARS = 120


def warranty_months(service: str | None) -> int | None:
    """Published warranty for a service family, or None when none is published."""
    folded = _fold(service)
    if not folded:
        return None
    words = set(folded.replace("de ", " ").split())
    for months, families in WARRANTY_MONTHS:
        for family in families:
            if all(term in words for term in family):
                return months
    return None


def _add_months(day: date, months: int) -> date:
    """Calendar month arithmetic: 04/08/2026 + 6 months is 04/02/2027."""
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    # A day that does not exist in the target month clamps to that month's end.
    while True:
        try:
            return day.replace(year=year, month=month)
        except ValueError:
            day = day.replace(day=day.day - 1)


def _local(moment: datetime, zone: ZoneInfo) -> datetime:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(zone)


def _day(moment: datetime, zone: ZoneInfo) -> str:
    return _local(moment, zone).strftime("%d/%m/%Y")


def _ago(moment: datetime, now: datetime) -> str:
    days = (now.date() - moment.date()).days
    if days <= 0:
        return "hoy"
    if days == 1:
        return "ayer"
    return f"hace {days} días"


def _equipment_line(equipment: CustomerEquipment) -> str:
    label = " ".join(
        part for part in (equipment.equipment_type, equipment.brand, equipment.model) if part
    )
    label = label or "Equipo"
    if equipment.age:
        label += f" ({equipment.age})"
    if equipment.details:
        label += f" — {_clip(equipment.details, MAX_EQUIPMENT_DETAIL_CHARS)}"
    return label


def _work_address(case: Case) -> str | None:
    """The address a work was done at, from the case's own snapshot."""
    bundle = case.bundle if isinstance(case.bundle, dict) else {}
    captured = bundle.get("captured") if isinstance(bundle.get("captured"), dict) else {}
    customer_snapshot = bundle.get("customer") if isinstance(bundle.get("customer"), dict) else {}
    return captured.get("address") or customer_snapshot.get("address") or None


def _work_line(case: Case, zone: ZoneInfo, now: datetime, home: str | None) -> str:
    day = _day(case.created_at, zone)
    service = case.service or "Trabajo sin servicio registrado"
    status = case.status or "abierto"
    line = f"- {day} · {service} · {status} · {_ago(_local(case.created_at, zone), _local(now, zone))}"
    address = _work_address(case)
    if address and _fold(address) != _fold(home):
        line += f" · en {address} (otra propiedad)"
    months = warranty_months(case.service)
    if months is not None:
        expires = _add_months(_local(case.created_at, zone).date(), months)
        line += f" · garantía vigente hasta {expires.strftime('%d/%m/%Y')} ({WARRANTY_NOTE[months]})"
    return line


def _decide_spending_line(value: str | None) -> str:
    if value == "no":
        return (
            "Decide el gasto: no. Esta persona no decide. No confirmes precio ni "
            "autorices trabajo: coordina con quien decide."
        )
    if value == "duda":
        return (
            "Decide el gasto: sin confirmar. Antes de hablar de precio o de "
            "autorizar el trabajo, pregunta una sola vez quién decide."
        )
    return "Decide el gasto: sí, esta persona decide la contratación y el pago."


def build_case_ficha(
    session: Session,
    customer_id: int,
    *,
    now: datetime | None = None,
    timezone_name: str = DEFAULT_TIMEZONE,
) -> str:
    """Render the bounded, deterministic ficha of one customer's case history.

    Empty string when there is nothing stored: a first contact injects no block,
    rather than a header with no content.
    """
    customer = session.get(Customer, customer_id)
    if customer is None:
        return ""
    now = now or datetime.now(timezone.utc)
    zone = ZoneInfo(timezone_name or DEFAULT_TIMEZONE)

    equipment = session.scalars(
        select(CustomerEquipment)
        .where(CustomerEquipment.customer_id == customer_id)
        .order_by(CustomerEquipment.created_at.desc(), CustomerEquipment.id.desc())
        .limit(MAX_EQUIPMENT_LINES)
    ).all()
    works = session.scalars(
        select(Case)
        .where(Case.customer_id == customer_id)
        .order_by(Case.created_at.desc(), Case.id.desc())
        .limit(MAX_WORK_LINES)
    ).all()
    appointment = session.scalar(
        select(Appointment)
        .where(
            Appointment.customer_id == customer_id,
            Appointment.status == AppointmentStatus.BOOKED,
            Appointment.starts_at > now,
        )
        .order_by(Appointment.starts_at)
        .limit(1)
    )

    address = customer.address or None
    home = f"{_clip(address, MAX_ADDRESS_CHARS)}, {_clip(customer.comuna, 60)}" if address and customer.comuna else _clip(address, MAX_ADDRESS_CHARS) or None
    decide_spending = getattr(customer, "decide_spending", "si")
    nothing_known = not home and not equipment and not works and appointment is None
    if nothing_known and decide_spending == "si":
        # A first contact: nothing has happened yet, so there is no case to state.
        return ""

    head: list[str] = ["Caso del cliente"]
    if home:
        head.append(f"Propiedad: {home}")
    elif customer.comuna:
        head.append(f"Propiedad: sin dirección registrada ({customer.comuna})")
    if equipment:
        head.append("Equipos: " + "; ".join(_equipment_line(item) for item in equipment))

    detail: list[str] = []
    if works:
        detail.append("Trabajos previos:")
        detail.extend(_work_line(case, zone, now, home) for case in works)
    pending = [case for case in works if case_is_open(case)]
    if pending:
        detail.append("Pendiente de nuestra parte:")
        detail.extend(
            f"- {case.service or 'Trabajo sin servicio registrado'} "
            f"(abierto desde el {_day(case.created_at, zone)})"
            for case in pending
        )
    if appointment is not None:
        detail.append(
            "Próxima visita: "
            f"{appointment.service} el {appointment.local_start.strftime('%d/%m/%Y %H:%M')}"
        )
    detail.append(_decide_spending_line(decide_spending))

    kept = list(head)
    truncated = False
    for line in detail:
        if len("\n".join([*kept, line])) > FICHA_MAX_CHARS:
            truncated = True
            break
        kept.append(line)
    if truncated:
        # Deterministic cut, never a half line: the ceiling is the contract.
        while len(kept) > 1 and len("\n".join([*kept, "…"])) > FICHA_MAX_CHARS:
            kept.pop()
        if len("\n".join([*kept, "…"])) <= FICHA_MAX_CHARS:
            kept.append("…")
        else:
            kept = [_clip(head[0], FICHA_MAX_CHARS)]
    return "\n".join(kept)
