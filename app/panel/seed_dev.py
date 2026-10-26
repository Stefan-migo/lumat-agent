"""Seed realistic development data after explicit operator confirmation."""

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
    Appointment, AppointmentHistory, AppointmentStatus, Case, Conversation, ConversationEvent,
    ConversationState, Customer, CustomerEquipment, CustomerNote, CustomerState, Memory,
    MemoryType, Message, MessageDirection, MessageStatus, MessageType, User, UserRole,
)
from app.services import memory as memory_service
from app.services.users import hash_password

MARKER = "5690000000"

CUSTOMERS = [
    ("Marcela Fuentes", "Ñuñoa", "Av. Italia 1234", "marcela@example.com"),
    ("Pedro Rojas", "Maipú", "Los Pajaritos 842", None),
    ("Ana Soto", "Providencia", "Manuel Montt 611", "ana.soto@example.com"),
    ("Jorge Valdés", "La Florida", "Vicuña Mackenna 4580", None),
    ("Carolina Muñoz", "Las Condes", "Apoquindo 3201", "carolina@example.com"),
    ("Luis Araya", "Macul", "Av. Quilín 2870", None),
    ("Paula Contreras", "San Miguel", "Gran Avenida 5220", None),
    ("Rodrigo Silva", "Peñalolén", "Consistorial 1740", "rodrigo@example.com"),
    ("Daniela Torres", "La Reina", "Príncipe de Gales 8060", None),
    ("Felipe Morales", "Santiago", "San Diego 1450", None),
    ("Verónica Castro", "Vitacura", "Las Hualtatas 9100", "vero@example.com"),
    ("Esteban Reyes", "Quilicura", "Lo Marcoleta 380", None),
]
CHAT = [
    ["Hola, el calefón está haciendo un ruido extraño.", "Hola Marcela, ¿se apaga o mantiene la llama?", "Se apaga después de unos minutos.", "Entiendo, coordinaremos una revisión."],
    ["Necesito una visita para revisar la caldera.", "Claro, ¿en qué comuna está?", "En Maipú, cerca del metro.", "Gracias, revisamos disponibilidad para esta semana."],
    ["Quedó pendiente la mantención anual.", "Podemos agendarla para mañana.", "Perfecto, en la mañana me sirve."],
    ["Siento olor a gas junto al calefont.", "Por seguridad, cierre la llave y ventile el lugar. ¿Ya lo hizo?"],
    ["La caldera marca un código de error.", "¿Me indica el modelo que aparece en la etiqueta?", "Es una Bosch Condens."],
    ["¿Cuánto cuesta revisar un calefón?", "La visita de diagnóstico tiene un valor desde $25.000."],
    ["El agua sale tibia y luego fría.", "¿Ocurre en todas las llaves?", "Sí, en toda la casa."],
    ["Quiero confirmar la hora de mañana.", "Su visita está confirmada para las 15:00."],
    ["La presión de la caldera bajó bastante.", "¿Puede enviarnos una foto del manómetro?", "La envío ahora."],
    ["Gracias, el equipo quedó funcionando bien.", "Qué bueno. Dejamos el servicio registrado."],
    ["¿Realizan mantención de caldera mural?", "Sí, trabajamos con distintas marcas.", "La mía es una Baxi."],
    ["Necesito ayuda con el calefón, no enciende.", "Cuénteme si aparece alguna luz o código."],
]
# One distinct conversation summary, case summary, operator note and equipment detail per customer,
# so the panel does not read as twelve copies of the same row.
SUMMARIES = [
    "Consulta por ruido y apagado intermitente del calefón.",
    "Solicitud de visita para revisar la caldera.",
    "Coordinación de la mantención anual pendiente.",
    "Reporte de olor a gas; se entregaron indicaciones de seguridad.",
    "Consulta por código de error de la caldera Bosch.",
    "Cotización de revisión de calefón.",
    "Reporte de agua tibia intermitente en toda la casa.",
    "Confirmación de la hora de la visita técnica.",
    "Consulta por baja presión de la caldera.",
    "Cierre de la reparación ya realizada por el técnico.",
    "Consulta por mantención de caldera mural.",
    "Calefón no enciende; cliente en Quilicura.",
]
CASE_SUMMARIES = [
    "Se coordinó revisión por ruido y apagado del calefón.",
    "Visita técnica agendada para revisar la caldera.",
    "Mantención anual de caldera por coordinar.",
    "Emergencia por olor a gas; se instruyó cerrar la llave y ventilar.",
    "Diagnóstico de código de error en caldera Bosch Condens.",
    "Cotización de diagnóstico de calefón solicitada por el cliente.",
    "Agua tibia intermitente; se evaluará el termostato.",
    "Visita confirmada; el cliente solicita puntualidad.",
    "Presión de caldera baja; se solicitó foto del manómetro.",
    "Servicio de reparación finalizado y confirmado por el cliente.",
    "Mantención de caldera mural Baxi solicitada.",
    "Calefón sin encender; caso derivado a atención humana.",
]
NOTES = [
    "Prefiere contacto durante la tarde.",
    "Cliente con historial de mantención anual.",
    "Solicita aviso por WhatsApp antes de la visita.",
    "Vive en edificio; coordinar acceso con conserjería.",
    "Tiene dos equipos: calefón y caldera.",
    "Pidió la cotización por escrito.",
    "Trabaja fuera de casa hasta las 18:00.",
    "Cliente frecuente; buen historial.",
    "Prefiere técnico con experiencia en calderas murales.",
    "Servicio cerrado; no contactar por ahora.",
    "Solicita recordatorio un día antes.",
    "Caso sensible; prefiere texto antes que llamados.",
]
EQUIPMENT = [
    ("calefón", "Junkers", "Hydro 11", "6 años", "Instalado en logia; revisar encendido y llama."),
    ("caldera", "Bosch", "Condens 2500", "4 años", "Mantención anual registrada; revisar presión."),
    ("calefón", "Mademsa", "ES 200", "8 años", "Presenta ruido al calentar; revisar ánodo."),
    ("caldera", "Baxi", "Nuvola 24", "3 años", "Mural; revisar purga y manómetro."),
    ("calefón", "Rheem", "Eco 16", "5 años", "Encendido irregular; limpiar quemador."),
]


def _remove_previous(session) -> None:
    customer_ids = select(Customer.id).where(Customer.phone_e164.like(f"+{MARKER}%"))
    conversation_ids = select(Conversation.id).where(Conversation.customer_id.in_(customer_ids))
    case_ids = select(Case.id).where(Case.customer_id.in_(customer_ids))
    memory_ids = select(cast(Customer.id, String)).where(Customer.phone_e164.like(f"+{MARKER}%"))
    session.execute(delete(Message).where(Message.conversation_id.in_(conversation_ids)))
    appointment_ids = select(Appointment.id).where(Appointment.case_id.in_(case_ids))
    session.execute(delete(AppointmentHistory).where(AppointmentHistory.appointment_id.in_(appointment_ids)))
    session.execute(delete(ConversationEvent).where(ConversationEvent.conversation_id.in_(conversation_ids)))
    session.execute(delete(Appointment).where(Appointment.case_id.in_(case_ids)))
    session.execute(delete(Case).where(Case.customer_id.in_(customer_ids)))
    session.execute(delete(CustomerEquipment).where(CustomerEquipment.customer_id.in_(customer_ids)))
    session.execute(delete(Conversation).where(Conversation.customer_id.in_(customer_ids)))
    session.execute(delete(CustomerNote).where(CustomerNote.customer_id.in_(customer_ids)))
    session.execute(delete(Memory).where(Memory.scope == "customer", Memory.entity_id.in_(memory_ids)))
    session.execute(delete(Customer).where(Customer.phone_e164.like(f"+{MARKER}%")))


def seed_dev() -> str:
    now = datetime.now(timezone.utc)
    zone = ZoneInfo("America/Santiago")
    with session_scope() as session:
        _remove_previous(session)
        technician = session.scalar(select(User).where(User.username == "mgonzalez"))
        if technician is None:
            technician = User(username="mgonzalez", password_hash=hash_password("seed-account-disabled"), role=UserRole.TECNICO, active=False)
            session.add(technician)
            session.flush()

        for i, (name, comuna, address, email) in enumerate(CUSTOMERS):
            at = now - timedelta(days=i * 2.4)
            consent = i % 3 != 1
            customer = Customer(phone_e164=f"+{MARKER}{i:02d}", name=name, comuna=comuna, address=address,
                email=email, state=list(CustomerState)[i % len(CustomerState)], consent_status=consent,
                consent_at=at if consent else None, created_at=at)
            session.add(customer)
            session.flush()
            state = ConversationState.CLOSED if i == 9 else ConversationState.HUMAN if i in (0, 3) else ConversationState.BOT
            at = now - timedelta(days=min(i * 2, 6))
            turns = CHAT[i]
            if i in (0, 3):
                turns = turns[:3] if len(turns) > 2 else [*turns, "Sí, gracias por la orientación."]
                turns[-1] = turns[-1] if i == 0 else "Ya cerré la llave y abrí las ventanas."
            if i == 11:
                turns = ["Hola, el calefón no enciende.", "¿Puede indicarnos la comuna?", "Estoy en Quilicura."]
            if i == 9:
                turns = ["Solicité una reparación la semana pasada.", "El técnico ya lo dejó operativo.", "Muchas gracias."]
            conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164, state=state,
                created_at=now - timedelta(days=min(i * 2, 28)), last_message_at=now - timedelta(minutes=10) if i in (0, 3, 11) else at + timedelta(minutes=len(turns)),
                closed_at=now - timedelta(days=3) if state == ConversationState.CLOSED else None,
                summary=SUMMARIES[i], responsible_id=technician.id if state == ConversationState.HUMAN else None)
            session.add(conversation)
            session.flush()
            for j, text in enumerate(turns):
                direction = MessageDirection.INBOUND if j % 2 == 0 else MessageDirection.OUTBOUND
                created = now - timedelta(minutes=20 - j * 5) if i in (0, 3, 11) else at + timedelta(minutes=j)
                session.add(Message(conversation_id=conversation.id, direction=direction, msg_type=MessageType.TEXT,
                    text=text, status=MessageStatus.RECEIVED if direction == MessageDirection.INBOUND else MessageStatus.PROCESSED, created_at=created))
            service = "visita" if i in (0, 2, 5, 8) else "caldera" if i % 2 else "calefont"
            open_case = i != 9
            emergency = i == 3
            case = Case(customer_id=customer.id, conversation_id=conversation.id, created_at=at, service=service,
                priority="urgente" if emergency else "alta" if i % 3 == 0 else "media",
                status="escalado" if i in (0, 3, 6) else "abierto" if open_case else "cerrado",
                summary=CASE_SUMMARIES[i],
                amount=25000 + i * 5000, responsible_id=technician.id if i % 2 == 0 else None,
                escalated_at=at if i in (0, 3, 6) else None, emergency=emergency,
                # i == 3 stays unacknowledged: the dev dashboard must show at least one
                # pending emergency, otherwise the Urgentes card is empty on a fresh seed.
                acknowledged_at=at + timedelta(minutes=10) if i in (0, 6) else None,
                closed_at=now - timedelta(days=2) if not open_case else None)
            session.add(case)
            session.flush()
            if i < 5:
                equipment_type, brand, model, age, details = EQUIPMENT[i]
                session.add(CustomerEquipment(customer_id=customer.id, equipment_type=equipment_type,
                    brand=brand, model=model, age=age, details=details, created_at=at))
                session.add(CustomerNote(customer_id=customer.id, author="operador", note=NOTES[i], created_at=at))
                memory_service.upsert(session, scope="customer", entity_id=str(customer.id), topic_key="contact_preference",
                    tipo=MemoryType.PREFERENCE, titulo="Preferencia de contacto", contenido=NOTES[i])
            if i < 6:
                local_start = datetime.combine(now.astimezone(zone).date(), time(15 + i % 3), tzinfo=zone)
                starts_at = local_start.astimezone(timezone.utc) if i == 0 else now + timedelta(days=i + 1)
                local = starts_at.astimezone(zone)
                session.add(Appointment(service=service, customer_id=customer.id, case_id=case.id, technician_id=technician.id,
                    local_start=local.replace(tzinfo=None), timezone="America/Santiago", starts_at=starts_at,
                    ends_at=starts_at + timedelta(hours=1), duration_minutes=60, status=AppointmentStatus.BOOKED))
    return "replaced dev rows: 12 customers, 12 conversations, 35 messages, 12 cases, 6 appointments"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="confirm replacing dev seed rows")
    parser.add_argument("--allow-nonlocal", action="store_true", help="allow a database host outside db/localhost")
    args = parser.parse_args(argv)
    database_url = make_url(get_settings().database_url)
    print(f"Target database: {database_url.render_as_string(hide_password=True)}", flush=True)
    print("Demo rows will be replaced.", flush=True)
    if database_url.host not in {"db", "localhost", "127.0.0.1"} and not args.allow_nonlocal:
        print("Refusing to write to a non-development host: pass --allow-nonlocal to override this host check.", file=sys.stderr)
        return 1
    if not (args.yes or os.environ.get("LUMAT_DEMO_SEED") == "1"):
        print("Refusing to write without explicit opt-in: pass --yes or set LUMAT_DEMO_SEED=1.", file=sys.stderr)
        return 1
    print(seed_dev(), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
