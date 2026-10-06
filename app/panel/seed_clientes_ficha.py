"""Seed one complete customer ficha and two light customer records.

Usage inside the API container::

    docker exec lumat-clientes-api-1 .venv/bin/python app/panel/seed_clientes_ficha.py --yes

The target URL is printed with its password redacted. Writing requires
``--yes`` or ``LUMAT_DEMO_SEED=1``; the resolved host must be ``db``,
``localhost``, or ``127.0.0.1`` unless ``--allow-nonlocal`` is also passed.
These checks defend against an accidental run, not a determined operator who
passes both flags. They do not prove that a local or named host is a development
database. Rows for the reserved ``+569111111`` phone prefix are replaced on
each run. The existing ``mgonzalez`` user is never modified or deleted.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import String, cast, delete, select
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
    CustomerEquipment,
    CustomerNote,
    CustomerState,
    Memory,
    MemoryType,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
    User,
    UserRole,
)
from app.services import memory as memory_service
from app.services.users import hash_password

MARKER = "569111111"


def _remove_previous(session) -> None:
    customer_ids = select(Customer.id).where(Customer.phone_e164.like(f"+{MARKER}%"))
    conversation_ids = select(Conversation.id).where(Conversation.customer_id.in_(customer_ids))
    case_ids = select(Case.id).where(Case.customer_id.in_(customer_ids))
    seeded_customer_ids = select(cast(Customer.id, String)).where(
        Customer.phone_e164.like(f"+{MARKER}%")
    )
    session.execute(delete(Message).where(Message.conversation_id.in_(conversation_ids)))
    session.execute(delete(Appointment).where(Appointment.case_id.in_(case_ids)))
    session.execute(delete(Case).where(Case.customer_id.in_(customer_ids)))
    session.execute(delete(CustomerEquipment).where(CustomerEquipment.customer_id.in_(customer_ids)))
    session.execute(delete(Conversation).where(Conversation.customer_id.in_(customer_ids)))
    session.execute(delete(CustomerNote).where(CustomerNote.customer_id.in_(customer_ids)))
    session.execute(delete(Memory).where(
        Memory.scope == "customer", Memory.entity_id.in_(seeded_customer_ids)
    ))
    session.execute(delete(Customer).where(Customer.phone_e164.like(f"+{MARKER}%")))


def _add_conversation(session, customer: Customer, *, state: ConversationState,
                      created_at: datetime, messages: list[tuple[MessageDirection, str]]) -> Conversation:
    conversation = Conversation(
        customer_id=customer.id,
        wa_phone=customer.phone_e164,
        state=state,
        created_at=created_at,
        last_message_at=created_at + timedelta(hours=len(messages)),
        closed_at=created_at + timedelta(hours=len(messages)) if state == ConversationState.CLOSED else None,
        summary="Coordinación y seguimiento de servicio técnico." if state == ConversationState.CLOSED else None,
    )
    session.add(conversation)
    session.flush()
    for index, (direction, text) in enumerate(messages):
        session.add(Message(
            conversation_id=conversation.id,
            direction=direction,
            msg_type=MessageType.TEXT,
            text=text,
            status=MessageStatus.RECEIVED if direction == MessageDirection.INBOUND else MessageStatus.PROCESSED,
            created_at=created_at + timedelta(hours=index),
        ))
    return conversation


def _add_appointment(session, *, customer: Customer, case: Case, technician: User,
                     starts_at: datetime, status: AppointmentStatus, zone: ZoneInfo) -> None:
    local_start = starts_at.astimezone(zone)
    session.add(Appointment(
        service=case.service or "visita técnica",
        customer_id=customer.id,
        case_id=case.id,
        technician_id=technician.id,
        local_start=local_start.replace(tzinfo=None),
        timezone="America/Santiago",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=60),
        duration_minutes=60,
        status=status,
    ))


def seed_clientes_ficha() -> str:
    """Replace this seeder's rows and report inserted fixture counts."""
    now = datetime.now(timezone.utc)
    zone = ZoneInfo("America/Santiago")
    with session_scope() as session:
        _remove_previous(session)
        technician = session.scalar(select(User).where(User.username == "mgonzalez"))
        if technician is None:
            technician = User(
                username="mgonzalez",
                password_hash=hash_password("seed-account-disabled"),
                role=UserRole.TECNICO,
                active=False,
            )
            session.add(technician)
            session.flush()

        rich = Customer(
            phone_e164=f"+{MARKER}1", name="Marcela Fuentes", email="marcela@example.com",
            address="Av. Italia 1234", comuna="Ñuñoa", state=CustomerState.POSTVENTA,
            consent_status=True, consent_at=now,
            created_at=datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc),
        )
        pedro = Customer(
            phone_e164=f"+{MARKER}2", name="Pedro Rojas", state=CustomerState.NUEVO,
            consent_status=False,
        )
        ana = Customer(
            phone_e164=f"+{MARKER}3", name="Ana Soto", state=CustomerState.FINALIZADO,
            consent_status=True, consent_at=now - timedelta(days=10),
        )
        session.add_all([rich, pedro, ana])
        session.flush()

        recent = now - timedelta(days=3)
        closed_conversation = _add_conversation(session, rich, state=ConversationState.CLOSED,
            created_at=now - timedelta(days=28), messages=[
                (MessageDirection.INBOUND, "Quisiera coordinar la mantención anual."),
                (MessageDirection.OUTBOUND, "Tenemos disponibilidad esta semana."),
                (MessageDirection.INBOUND, "Gracias, quedó funcionando muy bien."),
            ])
        active_conversation = _add_conversation(session, rich, state=ConversationState.BOT,
            created_at=recent, messages=[
                (MessageDirection.INBOUND, "El calefón no enciende."),
                (MessageDirection.OUTBOUND, "¿Podemos coordinar una visita?"),
                (MessageDirection.INBOUND, "Sí, prefiero contacto por la tarde."),
            ])
        open_case = Case(
            customer_id=rich.id, conversation_id=active_conversation.id,
            created_at=recent, service="Reparación de calefón", status="abierto",
            priority="alta", summary="Cliente reporta calefón que no enciende.",
            responsible_id=technician.id, amount=45000, emergency=False,
        )
        closed_cases = [
            Case(customer_id=rich.id, conversation_id=closed_conversation.id,
                 created_at=now - timedelta(days=180), service="Mantención de caldera",
                 status="cerrado", summary="Mantención anual realizada y equipo operativo.",
                 closed_at=now - timedelta(days=179)),
            Case(customer_id=rich.id, conversation_id=closed_conversation.id,
                 created_at=now - timedelta(days=90), service="Cambio de termostato",
                 status="cerrado", summary="Termostato reemplazado y temperatura verificada.",
                 closed_at=now - timedelta(days=89)),
        ]
        session.add_all([open_case, *closed_cases])
        session.flush()

        for appointment_case, offset, status in [
            (open_case, 7, AppointmentStatus.BOOKED),
            (open_case, 21, AppointmentStatus.BOOKED),
            (closed_cases[0], -120, AppointmentStatus.COMPLETED),
            (closed_cases[1], -60, AppointmentStatus.COMPLETED),
        ]:
            _add_appointment(session, customer=rich, case=appointment_case, technician=technician,
                starts_at=now + timedelta(days=offset), status=status, zone=zone)

        for offset, note in [
            (-12, "Prefiere contacto por la tarde."),
            (-2, "Cliente con historial de mantención anual."),
        ]:
            session.add(CustomerNote(customer_id=rich.id, author="operador", note=note,
                                     created_at=now + timedelta(days=offset)))
        session.add_all([
            CustomerEquipment(customer_id=rich.id, equipment_type="calefont", brand="Junkers",
                model="Hydro 11", age="6 años", details="Instalado en logia; revisar encendido.",
                created_at=now - timedelta(days=4)),
            CustomerEquipment(customer_id=rich.id, equipment_type="caldera", brand="Bosch",
                model="Condens 2500", age="4 años", details="Mantención anual registrada.",
                created_at=now - timedelta(days=3)),
        ])
        for topic_key, tipo, title, content in [
            ("customer_memo", MemoryType.CUSTOMER_MEMO, "Memoria del cliente",
             "Consulta por calefón que no enciende; prefiere contacto por la tarde."),
            ("contact_preference", MemoryType.PREFERENCE, "Preferencia de contacto",
             "Prefiere que la contacten durante la tarde."),
            ("annual_maintenance", MemoryType.DISCOVERY, "Historial de mantención",
             "Cuenta con historial de mantención anual de caldera."),
        ]:
            memory_service.upsert(session, scope="customer", entity_id=str(rich.id),
                topic_key=topic_key, tipo=tipo, titulo=title, contenido=content)

        for customer, state, case_status, text in [
            (pedro, ConversationState.BOT, "abierto", "Consulta por una visita técnica."),
            (ana, ConversationState.CLOSED, "cerrado", "Servicio finalizado y confirmado."),
        ]:
            conversation = _add_conversation(session, customer, state=state,
                created_at=now - timedelta(days=2), messages=[
                    (MessageDirection.INBOUND, text),
                    (MessageDirection.OUTBOUND, "Gracias, dejamos registro de tu solicitud."),
                ])
            session.add(Case(customer_id=customer.id, conversation_id=conversation.id,
                created_at=now - timedelta(days=2), service="Servicio técnico",
                status=case_status, summary=text,
                closed_at=now - timedelta(days=1) if case_status == "cerrado" else None))

    return "replaced ficha rows: 3 customers, 4 conversations, 10 messages, 5 cases, 4 appointments, 2 notes, 2 equipment records, 3 memories"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="confirm replacing ficha seed rows")
    parser.add_argument("--allow-nonlocal", action="store_true", help="allow a database host outside db/localhost")
    args = parser.parse_args(argv)
    database_url = make_url(get_settings().database_url)
    print(f"Target database: {database_url.render_as_string(hide_password=True)}", flush=True)
    print("Seeded rows will be replaced.", flush=True)
    if database_url.host not in {"db", "localhost", "127.0.0.1"} and not args.allow_nonlocal:
        print("Refusing to write to a non-development host: pass --allow-nonlocal to override this host check.", file=sys.stderr)
        return 1
    if not (args.yes or os.environ.get("LUMAT_DEMO_SEED") == "1"):
        print("Refusing to write without explicit opt-in: pass --yes or set LUMAT_DEMO_SEED=1.", file=sys.stderr)
        return 1
    print(seed_clientes_ficha(), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
