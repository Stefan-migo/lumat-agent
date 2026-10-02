"""Seed development-only dashboard data (never part of the deploy seed).

Usage inside the API container, where the environment variables and ``db``
Compose hostname are available::

    docker compose exec api python app/panel/seed_demo.py --yes

Alternatively, run from the repository root with the required environment
variables exported and a ``.venv`` installed::

    .venv/bin/python app/panel/seed_demo.py --yes

The target URL is printed with its password redacted, and writing requires
``--yes`` or ``LUMAT_DEMO_SEED=1``. Demo rows are replaced on each run. The
reserved ``+5690000000`` phone prefix identifies every seeded customer.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.engine import make_url

from app.config import get_settings
from app.db import session_scope
from app.models import (
    Appointment,
    AppointmentStatus,
    Case,
    Conversation,
    ConversationState,
    Customer,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
    User,
    UserRole,
)
from app.services.users import hash_password

MARKER = "5690000000"


def _remove_previous(session) -> None:
    customer_ids = select(Customer.id).where(Customer.phone_e164.like(f"+{MARKER}%"))
    conversation_ids = select(Conversation.id).where(Conversation.customer_id.in_(customer_ids))
    case_ids = select(Case.id).where(Case.customer_id.in_(customer_ids))
    session.execute(delete(Appointment).where(Appointment.case_id.in_(case_ids)))
    session.execute(delete(Case).where(Case.customer_id.in_(customer_ids)))
    session.execute(delete(Message).where(Message.conversation_id.in_(conversation_ids)))
    session.execute(delete(Conversation).where(Conversation.customer_id.in_(customer_ids)))
    session.execute(delete(Customer).where(Customer.phone_e164.like(f"+{MARKER}%")))
    session.execute(delete(User).where(User.username == f"{MARKER}technician"))


def seed_demo() -> str:
    """Replace this seeder's rows and report the inserted fixture counts."""
    now = datetime.now(timezone.utc)
    created = 0
    with session_scope() as session:
        _remove_previous(session)
        technician = User(
            username=f"{MARKER}technician",
            password_hash=hash_password("demo-dashboard-account-disabled"),
            role=UserRole.TECNICO,
            active=False,
        )
        session.add(technician)
        session.flush()
        for day_offset in range(30):
            at = now - timedelta(days=day_offset)
            customer = Customer(
                phone_e164=f"+{MARKER}{day_offset:02d}",
                name=f"Demo Customer {day_offset + 1}",
                created_at=at,
            )
            session.add(customer)
            session.flush()
            conversation = Conversation(
                customer_id=customer.id,
                wa_phone=customer.phone_e164,
                state=ConversationState.BOT,
                created_at=at,
                last_message_at=at,
            )
            session.add(conversation)
            session.flush()
            session.add(
                Message(
                    conversation_id=conversation.id,
                    direction=MessageDirection.INBOUND,
                    msg_type=MessageType.TEXT,
                    text="Demo dashboard inquiry",
                    status=MessageStatus.RECEIVED,
                    created_at=at,
                )
            )
            service = (
                "visita"
                if day_offset % 3 == 0
                else ("caldera" if day_offset % 2 else "calefont")
            )
            case = Case(
                customer_id=customer.id,
                conversation_id=conversation.id,
                created_at=at,
                service=service,
                priority="alta" if day_offset == 0 else "media",
                status="escalado" if day_offset % 5 == 0 else "abierto",
                emergency=day_offset == 0,
                summary="Demo dashboard case",
                escalated_at=at if day_offset % 5 == 0 else None,
            )
            session.add(case)
            session.flush()
            if day_offset == 0:
                # Use Santiago's local wall-clock day for the HOY projection.
                zone = ZoneInfo("America/Santiago")
                local_now = now.astimezone(zone)
                local_start = datetime.combine(
                    local_now.date(), time(15), tzinfo=local_now.tzinfo
                )
                starts_at = local_start.astimezone(timezone.utc)
                session.add(
                    Appointment(
                        service="visita",
                        customer_id=customer.id,
                        case_id=case.id,
                        technician_id=technician.id,
                        local_start=local_start.replace(tzinfo=None),
                        timezone="America/Santiago",
                        starts_at=starts_at,
                        ends_at=starts_at + timedelta(minutes=60),
                        duration_minutes=60,
                        status=AppointmentStatus.BOOKED,
                    )
                )
            created += 1
    return f"replaced demo rows: {created} customers, conversations, inbound messages, and cases; 1 appointment"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--yes", action="store_true", help="confirm replacing demo rows in the target database"
    )
    args = parser.parse_args(argv)
    database_url = make_url(get_settings().database_url)
    print(
        f"Target database: {database_url.render_as_string(hide_password=True)}\n"
        "Demo rows will be replaced.",
        flush=True,
    )
    if not (args.yes or os.environ.get("LUMAT_DEMO_SEED") == "1"):
        print(
            "Refusing to write without explicit opt-in: pass --yes or set LUMAT_DEMO_SEED=1.",
            file=sys.stderr,
        )
        return 1
    print(seed_demo())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
