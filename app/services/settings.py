"""Settings KV service (design: app/services/settings.py, D5; SS-1..5 storage).

All operational configuration lives in the single `settings` table (key PK,
value jsonb, updated_by FK->users, updated_at) — no per-domain config tables
(D5). This module provides the generic read/write surface:

- `get_setting`: stored value, else the built-in default for a known key, else
  the caller-provided default.
- `set_setting`: UPSERT + one audit entry per write (SH-5: who/what/when).

T4.1.2 adds the semantic accessors (scope rules / emergency keywords / tone /
standard messages) and their defaults on top of the generic KV surface:

- `get_scope_mode(session, category)` — SS-1: `bot_resolve` | `always_escalate`,
  default `bot_resolve` for any category not explicitly set.
- `get_emergency_keywords(session)` — SS-2: the EM-1 keyword list as plain
  strings, ready for T4.2's regex compiler; default list below.
- `get_tone(session)` / `get_message(session, key, default)` — SS-5: tone style
  and standard-message overrides.

All functions take an explicit session; the caller commits and closes (matches
app/services/customers.py / audit.py style).
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Settings
from app.services.audit import record_audit

logger = logging.getLogger(__name__)
_MESSAGE_TEMPLATE_SLOT_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")

ALLOWED_MESSAGE_TEMPLATE_SLOTS: frozenset[str] = frozenset(
    {
        "nombre",
        "comuna",
        "direccion",
        "equipo",
        "problema",
        "disponibilidad",
        "visita",
    }
)
MESSAGE_TEMPLATES_KEY = "messages.templates"
# S7: per-field fallback text for the capture questions. The code decides which
# field is missing; this key only holds the wording, so the order stays in code
# (`chat.conduct.orden` in T10).
CAPTURE_QUESTIONS_KEY = "capture.questions"

# S10: the conduct object — capture order, question budget per message and
# active derivation rules. Closed options only: the five invariants of S19 are
# NOT configurable and stay out of this key.
CHAT_CONDUCT_KEY = "chat.conduct"
# S5: the capture-phrasing switch. #687 removed this key because nothing read
# it; `phrasing.phrase` reads it now, so it comes back with a consumer and stays
# optional on save so payloads from a panel that does not render it still work.
CONDUCT_REDACCIONES: tuple[str, ...] = ("llm", "plantilla")
CONDUCT_OPTIONAL_KEYS: frozenset[str] = frozenset({"redaccion"})
CONDUCT_MAX_PREGUNTAS: tuple[int, ...] = (1, 2)
# The closed list of derivation rules (S10): exactly the ones the derivation
# logic reads. T10 listed five and T15 implemented `cobertura`; S4 removed the
# other four, which gated nothing and were dead configuration the panel could
# neither explain nor save back. `get_conduct` filters a stored row down to this
# list, so a row saved while they were accepted keeps loading.
CONDUCT_DERIVACIONES: tuple[str, ...] = ("cobertura",)
CHAT_CONDUCT_DEFAULTS: dict[str, Any] = {
    "orden": ["failure", "equipment", "comuna", "availability", "name", "email", "address"],
    "redaccion": "plantilla",
    "max_preguntas_por_mensaje": 1,
    "derivaciones": list(CONDUCT_DERIVACIONES),
}

# S12: the editable persona. The bundled `agent/personas/*.md` files stay the
# default (byte-coupled to `prompts.FALLBACKS`), so this key only holds the
# owner's override: "restore default" is deleting the row, never writing a copy
# of the shipped text. Both files are one unit — the brief is appended to the
# persona by `respond`, and a persona without its brief is incoherent.
PERSONA_TEXTS_KEY = "persona.texts"
PERSONA_PROMPT_KEYS: tuple[str, ...] = (
    "personas/orchestrator.md",
    "personas/orchestrator_brief.md",
)
PERSONA_TEXT_MAX_CHARS = 8000

# S13: the safety protocol the emergency node delivers. One key = one row = one
# audited version, so version/diff/restore sees one state per save. The
# deterministic gate (`emergency.keywords`) stays a separate key and the node
# never needs these rows to fire.
EMERGENCY_PROTOCOL_KEY = "emergency.protocol"
EMERGENCY_PROTOCOL_LISTS: tuple[str, ...] = ("safety_instructions", "contacts")
EMERGENCY_PROTOCOL_FIELDS: tuple[str, ...] = (*EMERGENCY_PROTOCOL_LISTS, "notify_message")

# S8: the deterministic (no-LLM) replies of booking, cancellation, rescheduling,
# handoff and the capture steps. The owner edits the wording, never the flow: the
# default is byte-for-byte the text the code shipped with.
REPLY_TEXTS_KEY = "reply.texts"
REPLY_TEXT_DEFAULTS: dict[str, str] = {
    "booking_offer": (
        "Tengo estos horarios disponibles para la visita técnica:\n"
        "{{opciones}}\n"
        "Responde con el número del horario que prefieres."
    ),
    "booking_unclear": (
        "No pude identificar un único horario. Responde con el número de una opción."
    ),
    # S1 (chatbot-experiencia): the approved copy for a day the offer exhausted.
    "booking_no_more_today": (
        "Para ese día no me quedan más horarios. Te propongo estos otros días:\n"
        "{{opciones}}\n"
        "Responde con el número del horario que prefieres."
    ),
    # S2 (agenda-preferencia): the requested day or franja has nothing, and the
    # offer moved forward. Naming what was asked is the "avisar" half of the rule;
    # a silent jump to another day is exactly what confused the measured customers.
    "booking_window_unavailable": (
        "Para {{momento}} no me quedan horarios. Te propongo estos:\n"
        "{{opciones}}\n"
        "Responde con el número del horario que prefieres."
    ),
    "booking_confirmed": "Tu visita técnica quedó confirmada para el {{fecha}} con {{tecnico}}.",
    "manage_no_visits": "No tienes visitas próximas para {{accion}}.",
    "manage_confirm_cancel": (
        "Tienes una visita el {{visita}}. ¿Confirmas que quieres cancelarla? "
        "Responde sí o no."
    ),
    "manage_select": (
        "¿Cuál visita quieres {{accion}}?\n"
        "{{opciones}}\n"
        "Responde con el número de la visita."
    ),
    "manage_slots_offer": (
        "Tengo estos horarios disponibles para reagendar tu visita:\n"
        "{{opciones}}\n"
        "Responde con el número del horario que prefieres."
    ),
    "manage_expired": (
        "La solicitud venció. Si aún necesitas gestionar tu visita, vuelve a escribirnos."
    ),
    "manage_appointment_unclear": (
        "No pude identificar una visita. Responde con el número de una opción."
    ),
    "manage_slots_unclear": (
        "No pude identificar un único horario. Responde con el número de una opción."
    ),
    "manage_kept": "De acuerdo, mantendremos tu visita agendada.",
    "manage_reschedule_unavailable": (
        "No puedo reagendar esta visita porque ya no está disponible."
    ),
    "manage_rescheduled": "Tu visita quedó reagendada para el {{fecha}}.",
    "manage_cancel_prompt": (
        "Responde sí para confirmar la cancelación o no para conservar la visita."
    ),
    "manage_cancel_unavailable": (
        "No puedo cancelar esta visita porque ya no está disponible para cancelación; "
        "su horario pudo haber comenzado o cambiado."
    ),
    "manage_cancelled": "Tu visita del {{visita}} quedó cancelada.",
    "handoff": "Un asesor revisará tu caso y te contactará a la brevedad.",
    # S4 (chatbot-experiencia): one approved text per derivation reason the
    # customer reads. The remaining reasons keep `handoff` above.
    "handoff_cobertura": (
        "Todavía no tenemos visitas técnicas en {{comuna}} para tu {{equipo}}, "
        "un asesor de Lumat se contactará contigo para ayudarte a la brevedad."
    ),
    "handoff_persona": (
        "Listo, te paso con una persona del equipo. En cuanto esté disponible te "
        "escribe por acá."
    ),
    "handoff_unknown_intent_thrice": (
        "No quiero seguir dándote vueltas con esto. Te dejo con una persona del "
        "equipo para que te ayude directamente."
    ),
    "handoff_campo_sin_respuesta": (
        "Veo que esa pregunta no te acomoda. Un asesor de Lumat te contacta para "
        "terminar de coordinar los datos."
    ),
    "handoff_booking_unavailable": (
        "No encontré un horario que nos sirva en la agenda, así que no te voy a "
        "dejar esperando: un asesor de Lumat te contacta para coordinar la visita "
        "directamente."
    ),
    "capture_evidence": "¿Tienes algo más para pasarle al técnico? (una foto, un audio…)",
    # S3 (chatbot-realismo-conversacional): one confirmation instead of four questions
    # when the customer record already holds the contact data.
    "capture_confirm_contact": (
        "Tengo {{comuna}} y {{direccion}}, con correo {{email}}. "
        "¿Sigue todo igual o cambió algo?"
    ),
    "capture_consent": (
        "¿Autorizas que guardemos tus datos para gestionar tu solicitud? Responde sí o no."
    ),
    "capture_consent_refused": "De acuerdo, no guardaremos tus datos ni agendaremos una visita.",
    "capture_consent_unclear": "Necesito que me confirmes si autorizas guardar tus datos. Responde sí o no.",
    # S1 (chatbot-realismo-conversacional): thanks for a data point, not for
    # showing up, and never with the name glued on — the greeting already used it.
    "capture_ack": "Entiendo. ",
}

# S8: the slots each reply may use. The owner can drop a slot from a text, never
# add one the call site does not fill: an unfilled `{{fecha}}` would reach the
# customer. `opciones` is the numbered list, `accion` the verb (cancelar /
# reagendar), `fecha` the appointment datetime, `visita` its full label,
# `comuna` the captured commune and `equipo` the corrected equipment for a
# coverage derivation (S5; optional when rendering legacy owner text).
REPLY_TEXT_SLOTS: dict[str, frozenset[str]] = {
    "booking_offer": frozenset({"opciones"}),
    "booking_unclear": frozenset(),
    "booking_no_more_today": frozenset({"opciones"}),
    "booking_window_unavailable": frozenset({"momento", "opciones"}),
    "booking_confirmed": frozenset({"fecha", "tecnico"}),
    "manage_no_visits": frozenset({"accion"}),
    "manage_confirm_cancel": frozenset({"visita"}),
    "manage_select": frozenset({"accion", "opciones"}),
    "manage_slots_offer": frozenset({"opciones"}),
    "manage_expired": frozenset(),
    "manage_appointment_unclear": frozenset(),
    "manage_slots_unclear": frozenset(),
    "manage_kept": frozenset(),
    "manage_reschedule_unavailable": frozenset(),
    "manage_rescheduled": frozenset({"fecha"}),
    "manage_cancel_prompt": frozenset(),
    "manage_cancel_unavailable": frozenset(),
    "manage_cancelled": frozenset({"visita"}),
    "handoff": frozenset(),
    "handoff_cobertura": frozenset({"comuna", "equipo"}),
    "handoff_persona": frozenset(),
    "handoff_unknown_intent_thrice": frozenset(),
    "handoff_campo_sin_respuesta": frozenset(),
    "handoff_booking_unavailable": frozenset(),
    "capture_evidence": frozenset(),
    "capture_confirm_contact": frozenset({"comuna", "direccion", "email"}),
    "capture_consent": frozenset(),
    "capture_consent_refused": frozenset(),
    "capture_consent_unclear": frozenset(),
    "capture_ack": frozenset({"nombre", "comuna", "equipo", "problema", "disponibilidad"}),
}

# SS-1: the two legal scope modes per category. Anything else behaves as unset.
SCOPE_MODES: tuple[str, ...] = ("bot_resolve", "always_escalate")
DEFAULT_SCOPE_MODE = "bot_resolve"

# SS-5: validated tone styles and their prompt directives.
TONE_STYLES: tuple[str, ...] = ("cercano", "formal", "directo")
TONE_DIRECTIVES: dict[str, str] = {
    "cercano": "Responde con un tono cercano, amable y claro.",
    "formal": "Responde con un tono formal, profesional y preciso.",
    "directo": "Responde de forma directa, breve y clara.",
}
DEFAULT_TONE_STYLE = "cercano"

MESSAGE_DEFAULTS: dict[str, str] = {
    "greeting": "Hola, soy Max, el asistente virtual de Lumat. ¿Con quién tengo el gusto? Cuéntame en qué te puedo ayudar.",
    "greeting_short": "Hola, soy Max, de Lumat. ¿Con quién tengo el gusto? Ya te ayudo con eso.",
    "greeting_name": "Hola, {{nombre}}. Soy Max, el asistente virtual de Lumat. ¿En qué te puedo ayudar?",
    "greeting_short_name": "Hola, {{nombre}}. Soy Max, de Lumat. Ya te ayudo con eso.",
    "smalltalk": "Con gusto. ¿En qué más te puedo ayudar?",
    "cannot_answer": (
        "Lo siento, no puedo responder con seguridad a eso. Un asesor de Lumat "
        "revisará tu consulta y te contactará."
    ),
    "clarification": (
        "Disculpa, no te entendí bien. ¿Me cuentas un poco más qué necesitas? "
        "Puedo ayudarte con una consulta, coordinar una visita técnica o "
        "revisar un trabajo ya hecho."
    ),
    "cannot_understand_offer": (
        "Perdón, no te entendí. ¿Prefieres que te tome tus datos para coordinar una visita, "
        "o que te atienda una persona?"
    ),
    "kb_miss_offer": (
        "No tengo ese dato. ¿Prefieres que te tome los datos para coordinar una visita, "
        "o que te atienda una persona?"
    ),
    "farewell": "¡Gracias por escribirnos! Que tengas buen día.",
    "out_of_hours": (
        "Estamos fuera de nuestro horario de atención. Te responderemos cuando "
        "volvamos a atender."
    ),
}

# SS-2 (EM-1): default emergency expressions + obvious Spanish variants.
# Stored as a plain list[str] — T4.2 compiles the regex from these.
DEFAULT_EMERGENCY_KEYWORDS: list[str] = [
    "olor a gas",
    "olor fuerte a gas",  # the adjective used to hide the phrase from the regex
    "huele a gas",  # variant
    "huelo gas",  # first person: the third person escalated, the first did not
    "huelo a gas",  # variant
    "fuga",
    "fuga de gas",  # variant
    "humo",
    "incendio",
    "chispa",
    "chispas",  # variant
    "explosión",
    "monóxido",
    "intoxicación",
    "riesgo eléctrico",
    "filtración severa",
]

# EM-3 (T4.2): safety protocol content delivered by the emergency node —
# approved safety steps, emergency contacts and the technician-notified
# confirmation. Panel-editable via the generic settings KV surface.
DEFAULT_SAFETY_INSTRUCTIONS: list[str] = [
    "Corta el suministro de gas solo si puedes hacerlo de forma segura.",
    "Abre puertas y ventanas para ventilar el lugar.",
    "No enciendas ni apagues luces, interruptores ni electrodomésticos.",
    "Sal del lugar si el olor a gas es fuerte y avisa desde afuera.",
    "No intentes reparar el equipo tú mismo.",
]
DEFAULT_EMERGENCY_CONTACTS: list[str] = [
    "Emergencias: Bomberos 132 o Ambulancia 131.",
    "Distribuidor de gas: el número de emergencia está en tu boleta o medidor.",
    "Lumat: +56 9 1234 5678.",
]
DEFAULT_EMERGENCY_NOTIFY_MESSAGE: str = (
    "Un técnico de Lumat ha sido notificado y te contactará a la brevedad."
)

# EM-4 (T4.3): owner/technician notification channel defaults. The WhatsApp
# utility template goes to the owner number (business-initiated send outside
# any 24h window — design D9); the email fallback / reminders use owner_email.
DEFAULT_OWNER_EMAIL: str = "emergencias@lumat.cl"
DEFAULT_OWNER_WHATSAPP: str = "+56912345678"
DEFAULT_SMTP_HOST: str = "localhost"
# Defaults keep the pre-WU-E behavior (a plain `smtplib.SMTP("localhost")` used
# port 25 with no auth/TLS), so an unconfigured install sends exactly as before.
DEFAULT_SMTP_PORT: int = 25
DEFAULT_SMTP_FROM: str = "notificaciones@lumat.cl"
DEFAULT_SMTP_USER: str = ""
DEFAULT_SMTP_TLS: str = "none"

# SS-3: USD per million tokens. Sources/effective date are retained in the
# default so a pricing change is auditable without a second configuration table.
DEFAULT_LLM_RATES = {
    "gpt-4o-mini": {"input_per_1m": 0.15, "output_per_1m": 0.60},
    "deepseek-chat": {"input_per_1m": 0.27, "output_per_1m": 1.10},
    "_source": "OpenAI and DeepSeek public API pricing; verify at activation",
    "_effective_date": "2026-09-11",
}

SERVICE_DURATIONS_KEY = "booking.service_durations"
# S1 (chatbot-experiencia): minutes of lead time before the first offered slot.
# Two hours is the owner's decision: the office has to be told and the
# technician has to get there, so a visit offered for "right now" is not real.
BOOKING_LEAD_MINUTES_KEY = "booking.lead_minutes"
BOOKING_LEAD_MINUTES_DEFAULT = 120
BOOKING_LEAD_MINUTES_MAX = 48 * 60
# A visit cannot reserve more than a day; anything longer is a typo, not intent.
MAX_SERVICE_DURATION_MINUTES = 1440

COVERAGE_COMMUNES_KEY = "coverage.communes"
# The seven communes the owner services. Matching is accent- and case-insensitive
# (see `normalize_comuna`); a name outside the list is coordinated with an
# advisor, never rejected outright.
DEFAULT_COVERAGE_COMMUNES = [
    "Las Condes",
    "Ñuñoa",
    "Lo Barnechea",
    "La Reina",
    "Peñalolén",
    "Colina",
    "Huechuraba",
]

TARIFA_PRECIOS_KEY = "tarifa.precios"
# The commercial catalogue. Prices live here, never in a customer-facing KB
# document: a date resolves to exactly one price, so an old season can never
# reach the model.
TARIFA_SERVICES = (
    "visita_tecnica",
    "mantencion_calefont",
    "mantencion_caldera",
    "lavado_red",
)
# Customer-facing service names for the prompt's <tarifario> block.
TARIFA_LABELS = {
    "visita_tecnica": "Visita técnica",
    "mantencion_calefont": "Mantención de calefont",
    "mantencion_caldera": "Mantención de caldera",
    "lavado_red": "Lavado de red",
}
# One or more month ranges per service (1-12, inclusive). The ranges must
# partition the year: no gaps, no overlaps. "Visita técnica" has a single
# all-year range; the three seasonal services have two.
DEFAULT_TARIFA_PRECIOS: dict[str, list[dict[str, int]]] = {
    "visita_tecnica": [{"desde_mes": 1, "hasta_mes": 12, "valor": 30000}],
    "mantencion_calefont": [
        {"desde_mes": 3, "hasta_mes": 10, "valor": 50000},
        {"desde_mes": 11, "hasta_mes": 2, "valor": 40000},
    ],
    "mantencion_caldera": [
        {"desde_mes": 3, "hasta_mes": 10, "valor": 80000},
        {"desde_mes": 11, "hasta_mes": 2, "valor": 60000},
    ],
    "lavado_red": [
        {"desde_mes": 3, "hasta_mes": 10, "valor": 140000},
        {"desde_mes": 11, "hasta_mes": 2, "valor": 120000},
    ],
}

# Built-in defaults for known keys. A missing row falls back to these instead
# of None, so unconfigured keys still behave (SS-1..5 "works out of the box").
# Fixed-message text is defined once in MESSAGE_DEFAULTS and expanded here for
# the generic settings KV fallback; get_message uses that same source directly.
SETTINGS_DEFAULTS: dict[str, Any] = {
    # SS-4: Meta service-message unit cost (USD), effective 2026-10-01.
    # Reference placeholder until verified with Meta at activation (T4.5).
    "meta_pricing": {"service_message_cost": 0.01},
    # SS-3: cost guardrail limits (USD) — per conversation and per UTC day.
    # T4.5 consumes them via costs.conversation_cost_state/daily_cost_state.
    "cost.conversation_limit": 1.50,
    "cost.daily_limit": 5.00,
    "cost.llm_rates": DEFAULT_LLM_RATES,
    # SS-1: category -> "bot_resolve" | "always_escalate". Empty = all resolve.
    "scope_rules": {},
    SERVICE_DURATIONS_KEY: {},    # S1: the commercial tariff, resolved by date before the prompt sees it.
    # S1 (chatbot-experiencia): lead time before the first offered slot.
    BOOKING_LEAD_MINUTES_KEY: BOOKING_LEAD_MINUTES_DEFAULT,
    TARIFA_PRECIOS_KEY: DEFAULT_TARIFA_PRECIOS,
    # S3: service coverage, matched without accents or case.
    COVERAGE_COMMUNES_KEY: DEFAULT_COVERAGE_COMMUNES,
    # SS-2: emergency keyword list consumed by T4.2's regex compiler.
    "emergency.keywords": DEFAULT_EMERGENCY_KEYWORDS,
    # S13: safety protocol content delivered by the emergency node (T4.2).
    # Editable as one unit: `emergency.protocol` carries all three fields.
    EMERGENCY_PROTOCOL_KEY: {
        "safety_instructions": DEFAULT_SAFETY_INSTRUCTIONS,
        "contacts": DEFAULT_EMERGENCY_CONTACTS,
        "notify_message": DEFAULT_EMERGENCY_NOTIFY_MESSAGE,
    },
    # EM-4: owner/technician notification channel (T4.3) — WhatsApp template
    # recipient + email fallback SMTP config. Panel-editable via the KV surface.
    "notify.owner_email": DEFAULT_OWNER_EMAIL,
    "notify.owner_whatsapp": DEFAULT_OWNER_WHATSAPP,
    "notify.reminder_template_name": "appointment_reminder_24h",
    "notify.followup_template_name": "appointment_followup",
    "notify.followup_no_show_template_name": "appointment_followup_no_show",
    # WU6: technician field quick-action templates (business-initiated; the two
    # Meta templates are created and approved externally — EXT).
    "notify.en_route_template_name": "en_route",
    "notify.arrived_template_name": "arrived",
    "notify.smtp_host": DEFAULT_SMTP_HOST,
    "notify.smtp_port": DEFAULT_SMTP_PORT,
    "notify.smtp_from": DEFAULT_SMTP_FROM,
    # WU-E: `notify.smtp_user` pairs with the encrypted `smtp_password` panel
    # secret (`app/services/smtp.py`); `notify.smtp_tls` is "none" | "starttls"
    # | "ssl". Both stay out of ASSISTANT_WRITABLE_SETTINGS (credentials).
    "notify.smtp_user": DEFAULT_SMTP_USER,
    "notify.smtp_tls": DEFAULT_SMTP_TLS,
    # SS-5: tone style used by the chat nodes.
    "tone.style": DEFAULT_TONE_STYLE,
    "capture.preventive_keywords": [
        "mantencion", "mantención", "mantenimiento", "revision", "revisión",
        "limpieza", "preventiva",
    ],
    **{f"messages.{key}": value for key, value in MESSAGE_DEFAULTS.items()},
    MESSAGE_TEMPLATES_KEY: [],
    "hours.timezone": "America/Santiago",
    "hours.schedule": [],
    "hours.closure_enabled": False,
    # AP-8 (T5.5): dashboard KPI time window in days (SQL counts over the
    # last N days). Panel-editable via the generic settings KV surface.
    "kpi.window_days": 7,
}


def get_setting(session: Session, key: str, default: Any = None) -> Any:
    """Read one setting: stored value > built-in default > caller default."""
    row = session.get(Settings, key)
    if row is not None:
        return row.value
    if key in SETTINGS_DEFAULTS:
        return SETTINGS_DEFAULTS[key]
    return default


def _collapse_whitespace(value: str) -> str:
    """Collapse runs of whitespace so a stray space cannot create a second name.

    Kept separate from `normalize_comuna`, which also folds case and accents: a
    service name is stored as the operator typed it, only its spacing is cleaned.
    """
    return " ".join(value.split())


def validate_service_durations(value: Any) -> dict[str, int]:
    """Validate the service -> minutes map before persistence.

    Keys are service names as they arrive from the conversation, so they are
    free text: what matters is that no two keys collapse under the same
    normalization, or one would silently shadow the other in
    `get_service_duration`.

    Whitespace is collapsed on the way in. A name is matched as a phrase against
    the customer's message, so "Mantención de  calefont" (a stray space, measured
    in production on 2026-10-29) answered nothing at all.
    """
    if not isinstance(value, dict):
        raise ValueError("booking.service_durations must be an object")

    normalized: dict[str, int] = {}
    seen: set[str] = set()
    for service, minutes in value.items():
        if not isinstance(service, str) or not service.strip():
            raise ValueError("booking.service_durations keys must be non-empty strings")
        name = _collapse_whitespace(service)
        key = normalize_comuna(name)
        if key in seen:
            raise ValueError(
                f"booking.service_durations has a duplicate service: {service!r}"
            )
        seen.add(key)
        if (
            not isinstance(minutes, int)
            or isinstance(minutes, bool)
            or not 1 <= minutes <= MAX_SERVICE_DURATION_MINUTES
        ):
            raise ValueError(
                "booking.service_durations values must be integers between 1 and "
                f"{MAX_SERVICE_DURATION_MINUTES} minutes"
            )
        normalized[name] = minutes
    return normalized


def get_service_durations(session: Session) -> dict[str, int]:
    """Return the configured durations, or an empty map when malformed."""
    value = get_setting(session, SERVICE_DURATIONS_KEY, default={})
    try:
        return validate_service_durations(value)
    except ValueError:
        return {}


def get_service_duration(
    session: Session, service: str | None, default: int = 60
) -> int:
    """Return a configured positive duration for a normalized service name."""
    if not isinstance(service, str) or not service.strip():
        return default

    durations = get_setting(session, "booking.service_durations", default={})
    if not isinstance(durations, dict):
        return default

    def normalize(value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", _collapse_whitespace(value).casefold())
        return "".join(char for char in decomposed if not unicodedata.combining(char))

    service_key = normalize(service)
    for key, duration in durations.items():
        if isinstance(key, str) and normalize(key) == service_key:
            if isinstance(duration, int) and not isinstance(duration, bool) and duration > 0:
                return duration
            return default
    return default


def get_booking_lead_minutes(session: Session) -> int:
    """Minutes of lead time before the first offered slot (decided: 120).

    A malformed stored value falls back to the default instead of blocking
    booking: this number guards the schedule, so it must never become the reason
    a customer cannot get a visit.
    """
    value = get_setting(
        session, BOOKING_LEAD_MINUTES_KEY, default=BOOKING_LEAD_MINUTES_DEFAULT
    )
    if isinstance(value, bool) or not isinstance(value, int):
        return BOOKING_LEAD_MINUTES_DEFAULT
    if value < 0 or value > BOOKING_LEAD_MINUTES_MAX:
        return BOOKING_LEAD_MINUTES_DEFAULT
    return value


def normalize_comuna(value: str) -> str:
    """Fold a commune name for matching: case, accents and inner spacing."""
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_accents.split())


def validate_coverage_communes(value: Any) -> list[str]:
    """Validate the coverage list before persistence and return it unchanged."""
    if not isinstance(value, list):
        raise ValueError("coverage.communes must be a list of commune names")

    seen: set[str] = set()
    for index, nombre in enumerate(value):
        if not isinstance(nombre, str) or not nombre.strip():
            raise ValueError(f"coverage.communes[{index}] must be a non-empty string")
        normalized = normalize_comuna(nombre)
        if normalized in seen:
            raise ValueError(f"coverage.communes has a duplicate commune: {nombre!r}")
        seen.add(normalized)
    return value


def get_coverage_communes(session: Session) -> list[str]:
    """Return the configured coverage, or the seven defaults when malformed."""
    value = get_setting(session, COVERAGE_COMMUNES_KEY, default=DEFAULT_COVERAGE_COMMUNES)
    try:
        return validate_coverage_communes(value)
    except ValueError:
        return DEFAULT_COVERAGE_COMMUNES


def comuna_cubierta(communes: list[str], nombre: str | None) -> bool:
    """True when ``nombre`` matches a covered commune under normalization."""
    if not isinstance(nombre, str):
        return False
    normalized = normalize_comuna(nombre)
    if not normalized:
        return False
    return any(normalize_comuna(item) == normalized for item in communes)


def get_tarifa_precios(session: Session) -> dict[str, list[dict[str, int]]]:
    """Return the configured tariff, or the default when unset or malformed."""
    value = get_setting(session, TARIFA_PRECIOS_KEY, default=DEFAULT_TARIFA_PRECIOS)
    try:
        return validate_tarifa_precios(value)
    except ValueError:
        return DEFAULT_TARIFA_PRECIOS


def tarifa_vigente(
    tarifa: dict[str, list[dict[str, int]]], fecha: date
) -> dict[str, int]:
    """Return the price in force for each service on ``fecha``.

    A service whose ranges do not cover that month is omitted rather than
    guessed, so the prompt never receives a figure the owner did not set.
    """
    vigente: dict[str, int] = {}
    for service, ranges in tarifa.items():
        for rango in ranges:
            if fecha.month in _tarifa_months(rango["desde_mes"], rango["hasta_mes"]):
                vigente[service] = rango["valor"]
                break
    return vigente


def _tarifa_months(desde_mes: int, hasta_mes: int) -> set[int]:
    """Expand one inclusive range, wrapping december -> january."""
    months: set[int] = set()
    month = desde_mes
    while True:
        months.add(month)
        if month == hasta_mes:
            return months
        month = month % 12 + 1


def validate_tarifa_precios(value: Any) -> dict[str, list[dict[str, int]]]:
    """Validate the tariff before persistence and return it unchanged.

    Shape: ``{service: [{"desde_mes", "hasta_mes", "valor"}, ...]}``. Each
    service must exist exactly once, every range must cover whole months, and
    the ranges of one service must partition months 1-12 (no gap, no overlap).
    """
    if not isinstance(value, dict):
        raise ValueError("tarifa.precios must be an object keyed by service")
    if set(value) != set(TARIFA_SERVICES):
        missing = sorted(set(TARIFA_SERVICES) - set(value))
        unknown = sorted(set(value) - set(TARIFA_SERVICES))
        raise ValueError(
            "tarifa.precios must cover exactly the known services "
            f"(missing: {missing}, unknown: {unknown})"
        )

    for service in TARIFA_SERVICES:
        ranges = value[service]
        if not isinstance(ranges, list) or not ranges:
            raise ValueError(f"tarifa.precios[{service!r}] must be a non-empty list")

        covered: set[int] = set()
        for index, rango in enumerate(ranges):
            if not isinstance(rango, dict):
                raise ValueError(f"tarifa.precios[{service!r}][{index}] must be an object")
            if set(rango) != {"desde_mes", "hasta_mes", "valor"}:
                raise ValueError(
                    f"tarifa.precios[{service!r}][{index}] must have exactly "
                    "desde_mes, hasta_mes and valor"
                )

            months = (rango["desde_mes"], rango["hasta_mes"])
            for month in months:
                if not isinstance(month, int) or isinstance(month, bool) or not 1 <= month <= 12:
                    raise ValueError(
                        f"tarifa.precios[{service!r}][{index}] months must be integers 1-12"
                    )
            valor = rango["valor"]
            if not isinstance(valor, int) or isinstance(valor, bool) or valor <= 0:
                raise ValueError(
                    f"tarifa.precios[{service!r}][{index}] valor must be a positive integer"
                )

            range_months = _tarifa_months(*months)
            overlap = covered & range_months
            if overlap:
                raise ValueError(
                    f"tarifa.precios[{service!r}] ranges overlap in months {sorted(overlap)}"
                )
            covered |= range_months

        missing_months = set(range(1, 13)) - covered
        if missing_months:
            raise ValueError(
                f"tarifa.precios[{service!r}] does not cover months {sorted(missing_months)}"
            )

    return value


def set_setting(
    session: Session,
    key: str,
    value: Any,
    *,
    updated_by: int | None = None,
    actor: str = "system",
) -> Settings:
    """Upsert one setting and audit the change (SH-5). The caller commits."""
    # SessionLocal runs autoflush=False, so a row inserted by an earlier call in
    # this session would be invisible to session.get -> flush so the upsert
    # reads its own writes (two set_setting calls per session stay one row).
    session.flush()
    row = session.get(Settings, key)
    before = row.value if row is not None else None
    if row is None:
        row = Settings(key=key, value=value, updated_by=updated_by)
        session.add(row)
    else:
        row.value = value
        row.updated_by = updated_by
    record_audit(
        session,
        actor=actor,
        action="settings.change",
        entity="settings",
        entity_id=key,
        before={"value": before} if before is not None else None,
        after={"value": value},
    )
    return row


def get_scope_mode(session: Session, category: str) -> str:
    """SS-1: mode for one category; `bot_resolve` when unset or invalid.

    `scope_rules` is a single JSONB dict (category -> mode), one UPSERT + one
    audit entry per panel save. Categories absent from the dict default to
    `bot_resolve`; a stored value outside the two literals behaves as unset.
    """
    rules = get_setting(session, "scope_rules", default={})
    mode = rules.get(category)
    return mode if mode in SCOPE_MODES else DEFAULT_SCOPE_MODE


def get_emergency_keywords(session: Session) -> list[str]:
    """SS-2: emergency keyword list (list[str]) or the EM-1 defaults.

    T4.2 compiles its detection regex from this list. Contract: stored value
    must be a list of strings — a malformed value is the panel's responsibility.

    S19: an empty or all-blank stored list is treated as "not configured" and
    degrades to the shipped triggers. An empty list compiles to a pattern that
    matches nothing, so honouring it would switch the gate off from data.
    """
    stored = get_setting(session, "emergency.keywords", default=DEFAULT_EMERGENCY_KEYWORDS)
    if isinstance(stored, list):
        keywords = [
            keyword.strip()
            for keyword in stored
            if isinstance(keyword, str) and keyword.strip()
        ]
        if keywords:
            return keywords
    return list(DEFAULT_EMERGENCY_KEYWORDS)


def get_tone(session: Session) -> str:
    """SS-5: valid tone style; invalid stored values degrade to the default."""
    tone = get_setting(session, "tone.style", default=DEFAULT_TONE_STYLE)
    return tone if tone in TONE_STYLES else DEFAULT_TONE_STYLE


def get_tone_directive(session: Session) -> str:
    """SS-5: prompt directive for the effective tone style."""
    return TONE_DIRECTIVES[get_tone(session)]


def get_hours_timezone(session: Session) -> str:
    """Return the configured IANA timezone, or the default when unusable."""
    timezone_name = get_setting(session, "hours.timezone", default="America/Santiago")
    return timezone_name if isinstance(timezone_name, str) else "America/Santiago"


def get_hours_schedule(session: Session) -> list[dict[str, Any]]:
    """Return the configured schedule, or the empty feature-off default."""
    schedule = get_setting(session, "hours.schedule", default=[])
    return schedule if isinstance(schedule, list) else []


def get_hours_closure_enabled(session: Session) -> bool:
    """Return whether the chat's out-of-hours closure gate is enabled."""
    enabled = get_setting(session, "hours.closure_enabled", default=False)
    return enabled if isinstance(enabled, bool) else False


def is_open_at(*, schedule: list, timezone_name: str, now: datetime) -> bool:
    """Evaluate a validated weekly schedule at an aware instant.

    Overnight windows are invalid because write-time validation requires
    ``open < close``; malformed entries fail open rather than closing chat.
    """
    if not schedule:
        return True

    try:
        local_now = now.astimezone(ZoneInfo(timezone_name))
    except (TypeError, ValueError, ZoneInfoNotFoundError) as exc:
        logger.warning("Unable to resolve hours timezone %r: %s", timezone_name, exc)
        return True

    parsed_entries: list[tuple[list[int], Any, Any]] = []
    for entry in schedule:
        try:
            if not isinstance(entry, dict):
                raise ValueError("entry is not an object")
            days = entry["days"]
            opening = entry["open"]
            closing = entry["close"]
            if (
                not isinstance(days, list)
                or not days
                or any(isinstance(day, bool) or not isinstance(day, int) or not 1 <= day <= 7 for day in days)
                or not isinstance(opening, str)
                or not isinstance(closing, str)
                or len(opening) != 5
                or len(closing) != 5
                or opening[2] != ":"
                or closing[2] != ":"
            ):
                raise ValueError("invalid days or HH:MM values")
            open_time = datetime.strptime(opening, "%H:%M").time()
            close_time = datetime.strptime(closing, "%H:%M").time()
            if open_time >= close_time:
                raise ValueError("open must be before close")
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Unable to parse hours schedule entry %r: %s", entry, exc)
            return True
        parsed_entries.append((days, open_time, close_time))

    weekday = local_now.isoweekday()
    local_time = local_now.time()
    return any(
        weekday in days and opening <= local_time < closing
        for days, opening, closing in parsed_entries
    )


def get_message(session: Session, key: str, default: str | None = None) -> str:
    """SS-5: override for `messages.<key>`, else the built-in default."""
    fallback = MESSAGE_DEFAULTS.get(key, default)
    return get_setting(session, f"messages.{key}", default=fallback)


def get_message_templates(session: Session) -> list[dict]:
    """Return the stored message-template list, or an empty list if malformed."""
    templates = get_setting(session, MESSAGE_TEMPLATES_KEY, default=[])
    return templates if isinstance(templates, list) else []


def get_capture_preventive_keywords(session: Session) -> list[str]:
    """Return configured preventive-service keywords, falling back when malformed."""
    value = get_setting(
        session,
        "capture.preventive_keywords",
        default=SETTINGS_DEFAULTS["capture.preventive_keywords"],
    )
    if isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value):
        return value
    return list(SETTINGS_DEFAULTS["capture.preventive_keywords"])


def get_capture_ack(session: Session) -> str:
    """Return the configurable acknowledgement, read from the reply catalog.

    `capture_ack` is a reply text like every other (S8): it lives in
    `reply.texts`, so the panel's reply editor, the slot whitelist and the
    shipped default stay one source of truth. An earlier shape stored it under
    `capture.ack` too, which made the catalog row the panel edits do nothing.
    """
    return get_reply_texts(session)["capture_ack"]


def get_capture_questions(session: Session) -> dict[str, str]:
    """Return the stored capture questions, or an empty map so the caller keeps
    its own defaults (the wording defaults live in `app/chat/nodes/capture.py`)."""
    value = get_setting(session, CAPTURE_QUESTIONS_KEY, default={})
    if not isinstance(value, dict):
        return {}
    kept = {
        field: text
        for field, text in value.items()
        if isinstance(field, str) and isinstance(text, str) and text.strip()
    }
    # F6 rejected slots at write time. A row saved before that (T7 accepted
    # them) would reach the client as literal braces, so it falls back to the
    # shipped wording instead of being served.
    with_slots = [
        field for field, text in kept.items() if "{{" in text or "}}" in text
    ]
    if with_slots:
        logger.warning(
            "capture.questions has legacy slots for %s; using the shipped wording",
            with_slots,
        )
    return {field: text for field, text in kept.items() if field not in with_slots}


def validate_message_templates(templates: Any) -> list[dict]:
    """Validate message templates before persistence and return them unchanged."""
    if not isinstance(templates, list):
        raise ValueError("Message templates must be a list")

    seen_ids: set[str] = set()
    for index, template in enumerate(templates):
        if not isinstance(template, dict):
            raise ValueError(f"Message template at index {index} must be an object")

        template_id = template.get("id")
        if not isinstance(template_id, str) or not template_id.strip():
            raise ValueError(f"Message template at index {index} must have a non-empty string id")
        if template_id in seen_ids:
            raise ValueError(f"Message template id {template_id!r} must be unique")
        seen_ids.add(template_id)

        text = template.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Message template {template_id!r} must have non-empty string text")
        unknown_slots = set(_MESSAGE_TEMPLATE_SLOT_RE.findall(text)) - ALLOWED_MESSAGE_TEMPLATE_SLOTS
        if unknown_slots:
            raise ValueError(
                f"Message template {template_id!r} contains unsupported slots: "
                f"{sorted(unknown_slots)}"
            )

    return templates


def validate_reply_texts(value: Any) -> dict[str, str]:
    """Validate the deterministic reply texts before persistence (S8).

    Every key needs text: a missing one would leave that branch with no reply.
    Slots are whitelisted per key, so the owner can simplify a text but cannot
    introduce a placeholder the call site does not know how to fill.
    """
    if not isinstance(value, dict):
        raise ValueError("reply.texts must be an object")

    missing = [
        key
        for key in REPLY_TEXT_DEFAULTS
        if not isinstance(value.get(key), str) or not value[key].strip()
    ]
    if missing:
        raise ValueError(f"reply.texts is missing text for: {missing}")

    unknown_keys = [key for key in value if key not in REPLY_TEXT_DEFAULTS]
    if unknown_keys:
        raise ValueError(f"reply.texts has unknown keys: {unknown_keys}")

    for key, allowed in REPLY_TEXT_SLOTS.items():
        unsupported = set(_MESSAGE_TEMPLATE_SLOT_RE.findall(value[key])) - allowed
        if unsupported:
            raise ValueError(
                f"reply.texts[{key!r}] contains unsupported slots: {sorted(unsupported)}"
            )

    return {key: value[key] for key in REPLY_TEXT_DEFAULTS}


def get_reply_texts(session: Session) -> dict[str, str]:
    """Configured deterministic replies, defaulting per key to the shipped text."""
    stored = get_setting(session, REPLY_TEXTS_KEY, default={})
    if not isinstance(stored, dict):
        stored = {}
    return {
        key: stored[key]
        if isinstance(stored.get(key), str) and stored[key].strip()
        else default
        for key, default in REPLY_TEXT_DEFAULTS.items()
    }


_FIXED_MESSAGE_LABELS: dict[str, str] = {
    "greeting": "saludo",
    "greeting_short": "saludo breve",
    "greeting_name": "saludo con nombre",
    "greeting_short_name": "saludo breve con nombre",
    "smalltalk": "mensaje de cortesía",
    "cannot_answer": "respuesta cuando no puede responder",
    "clarification": "aclaración",
    "cannot_understand_offer": "oferta cuando no entiende",
    "kb_miss_offer": "oferta cuando no tiene ese dato",
    "farewell": "despedida",
    "out_of_hours": "aviso fuera de horario",
}


def validate_fixed_messages(value: Any) -> dict[str, str]:
    """Reject mustache slots the fixed-message renderer cannot fill.

    Only the two name greetings render `{{nombre}}`; all other fixed messages
    are delivered verbatim and therefore reject both opening and closing braces.
    """
    if not isinstance(value, dict):
        raise ValueError("messages must be an object")

    for key, label in _FIXED_MESSAGE_LABELS.items():
        text = value.get(key)
        if not isinstance(text, str):
            raise ValueError(f"{label} debe ser texto")
        if key in {"greeting_name", "greeting_short_name"}:
            remainder = text.replace("{{nombre}}", "")
            if "{{" in remainder or "}}" in remainder:
                raise ValueError(
                    f"El {label} solo admite el marcador exacto {{{{nombre}}}}."
                )
        elif "{{" in text or "}}" in text:
            raise ValueError(f"El {label} no admite llaves de plantilla.")

    return {key: value[key] for key in _FIXED_MESSAGE_LABELS}


def validate_capture_questions(value: Any, fields: Sequence[str]) -> dict[str, str]:
    """Validate the per-field fallback questions before persistence (S7).

    `fields` is the effective capture order. Every field needs text because the
    fallback path has nothing else to ask, and an extra key would be dead config
    that silently outlives the field.

    Slots are rejected: nothing renders `capture.questions`, so `{{nombre}}`
    would reach the client as literal braces. F3 shipped the LLM-redaction path
    without a reader, so the contract is plain text until a renderer exists.
    """
    if not isinstance(value, dict):
        raise ValueError("capture.questions must be an object")

    missing = [
        field
        for field in fields
        if not isinstance(value.get(field), str) or not value[field].strip()
    ]
    if missing:
        raise ValueError(f"capture.questions is missing text for: {missing}")

    unknown_fields = [field for field in value if field not in fields]
    if unknown_fields:
        raise ValueError(f"capture.questions has unknown fields: {unknown_fields}")

    for field in fields:
        if "{{" in value[field] or "}}" in value[field]:
            raise ValueError(
                f"capture.questions[{field!r}] must not contain '{{{{' or '}}}}': "
                "the question is sent verbatim"
            )

    return {field: value[field] for field in fields}


def validate_conduct(
    value: Any, fields: Sequence[str], previous: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Validate the conduct object before persistence (S10).

    `fields` is the capture model's field list, passed by the caller so that
    `settings` never imports `capture` (same shape as
    `validate_capture_questions`). A field dropped from `orden` is the owner
    turning that ask off; an unknown field would be dead config, a repeat would
    ask the same field twice, and identity before `availability` would ask for
    the name before the customer agreed to the visit.
    """
    if not isinstance(value, dict):
        raise ValueError("chat.conduct must be an object")

    # As with other bounded settings, unknown top-level keys are ignored by the
    # returned projection. This also makes legacy `redaccion` data harmless.
    missing = [
        key for key in CHAT_CONDUCT_DEFAULTS
        if key not in value and key not in CONDUCT_OPTIONAL_KEYS
    ]
    if missing:
        raise ValueError(f"chat.conduct is missing: {missing}")

    orden = value["orden"]
    if not isinstance(orden, list) or not orden:
        raise ValueError("chat.conduct.orden must be a non-empty list of fields")
    unknown_fields = [field for field in orden if field not in fields]
    if unknown_fields:
        raise ValueError(f"chat.conduct.orden has unknown fields: {unknown_fields}")
    repeated = sorted({field for field in orden if orden.count(field) > 1})
    if repeated:
        raise ValueError(f"chat.conduct.orden repeats fields: {repeated}")
    if "availability" in orden:
        availability_at = orden.index("availability")
        too_early = [
            field
            for field in ("name", "email", "address")
            if field in orden and orden.index(field) < availability_at
        ]
        if too_early:
            raise ValueError(
                f"chat.conduct.orden asks identity before availability: {too_early}"
            )

    max_preguntas = value["max_preguntas_por_mensaje"]
    if isinstance(max_preguntas, bool) or max_preguntas not in CONDUCT_MAX_PREGUNTAS:
        raise ValueError(
            "chat.conduct.max_preguntas_por_mensaje must be one of "
            f"{list(CONDUCT_MAX_PREGUNTAS)}"
        )

    derivaciones = value["derivaciones"]
    if not isinstance(derivaciones, list):
        raise ValueError("chat.conduct.derivaciones must be a list of rules")
    unknown_rules = [rule for rule in derivaciones if rule not in CONDUCT_DERIVACIONES]
    if unknown_rules:
        raise ValueError(f"chat.conduct.derivaciones has unknown rules: {unknown_rules}")

    # S5: a payload that does not carry the switch must not switch it off. The
    # panel only renders the keys it knows, so every save from a panel without
    # the control arrives here without `redaccion`; keeping the stored value is
    # what stops an unrelated edit (the capture order) from silently resetting an
    # owner's explicit choice. An explicit value always wins, and an unknown one
    # in the payload is still an error.
    if "redaccion" in value:
        redaccion = value["redaccion"]
        if redaccion not in CONDUCT_REDACCIONES:
            raise ValueError(
                f"chat.conduct.redaccion must be one of {list(CONDUCT_REDACCIONES)}"
            )
    else:
        stored_mode = (previous or {}).get("redaccion")
        redaccion = (
            stored_mode
            if stored_mode in CONDUCT_REDACCIONES
            else CHAT_CONDUCT_DEFAULTS["redaccion"]
        )

    return {
        "orden": list(orden),
        "redaccion": redaccion,
        "max_preguntas_por_mensaje": max_preguntas,
        "derivaciones": list(derivaciones),
    }


def get_conduct(session: Session) -> dict[str, Any]:
    """Configured conduct, falling back per key to the shipped default (S10).

    S4: `derivaciones` is filtered down to the closed list of rules the logic
    reads. A row saved while the four phantom rules were still accepted keeps
    loading, and the panel never receives a rule it cannot save back. An empty
    list is a real value — the owner turned every derivation off — so it is not
    replaced by the default; only a missing or malformed value falls back.
    """
    stored = get_setting(session, CHAT_CONDUCT_KEY, default={})
    if not isinstance(stored, dict):
        stored = {}
    conduct = {
        key: stored.get(key) or (list(default) if isinstance(default, list) else default)
        for key, default in CHAT_CONDUCT_DEFAULTS.items()
    }
    rules = stored.get("derivaciones")
    if isinstance(rules, list):
        conduct["derivaciones"] = [
            rule for rule in rules if rule in CONDUCT_DERIVACIONES
        ]
    # Same treatment for the phrasing switch: a value stored before the key was
    # retired (or written by hand) must not reach the panel as an invalid option.
    if conduct.get("redaccion") not in CONDUCT_REDACCIONES:
        conduct["redaccion"] = CHAT_CONDUCT_DEFAULTS["redaccion"]
    return conduct


# Frente 2 unit 3: the exact setting keys the panel assistant may PROPOSE for a
# write. The write itself is approval-gated by the tool contract; this allowlist
# is the server-side bound. It deliberately excludes safety/routing/cost/notify
# keys (emergency.*, scope_rules, cost.*, meta_pricing, notify.*, kpi.*).
ASSISTANT_WRITABLE_SETTINGS: frozenset[str] = frozenset(
    {
        "tone.style",
        "messages.greeting",
        "messages.greeting_short",
        "messages.greeting_name",
        "messages.greeting_short_name",
        "messages.smalltalk",
        "messages.farewell",
        "messages.clarification",
        "messages.cannot_answer",
        "messages.out_of_hours",
        "hours.timezone",
        "hours.schedule",
    }
)

_ASSISTANT_MESSAGE_KEYS: frozenset[str] = frozenset(
    key for key in ASSISTANT_WRITABLE_SETTINGS if key.startswith("messages.")
)

# A runaway model string must not bloat a stored message; the schedule is already
# bounded (each entry contributes >=1 unique weekday, and weekdays cannot repeat,
# so at most 7 entries).
ASSISTANT_MESSAGE_MAX_LENGTH = 2000


def validate_assistant_setting(key: str, value: Any) -> None:
    """Validate one assistant-proposed setting; raise ValueError when unsafe.

    Guards the approval-gated `settings.update` tool: the key must be in the
    curated allowlist and the value must pass the same shape rules the panel's
    own Settings routes enforce (routes/settings.py).
    """
    if key not in ASSISTANT_WRITABLE_SETTINGS:
        raise ValueError(f"setting key is not assistant-writable: {key!r}")
    if key == "tone.style":
        if value not in TONE_STYLES:
            raise ValueError(f"tone.style must be one of {TONE_STYLES}")
    elif key in _ASSISTANT_MESSAGE_KEYS:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a non-empty string")
        if key not in {"messages.greeting_name", "messages.greeting_short_name"} and ("{{" in value or "}}" in value):
            raise ValueError(f"{key} must not contain '{{{{' or '}}}}'")
        if key in {"messages.greeting_name", "messages.greeting_short_name"}:
            slots = set(_MESSAGE_TEMPLATE_SLOT_RE.findall(value))
            if slots - {"nombre"} or value.count("{{") != value.count("}}"):
                raise ValueError(f"{key} only supports the {{nombre}} slot")
        if len(value) > ASSISTANT_MESSAGE_MAX_LENGTH:
            raise ValueError(f"{key} must be at most {ASSISTANT_MESSAGE_MAX_LENGTH} characters")
    elif key == "hours.timezone":
        if not isinstance(value, str) or not value.strip():
            raise ValueError("hours.timezone must be a non-empty IANA timezone")
        try:
            ZoneInfo(value)
        except (TypeError, ValueError, ZoneInfoNotFoundError):
            raise ValueError("hours.timezone must be a valid IANA timezone")
    elif key == "hours.schedule":
        validate_hours_schedule(value)


def validate_hours_schedule(schedule: Any) -> None:
    if not isinstance(schedule, list):
        raise ValueError("hours.schedule must be a list of objects")
    seen_days: set[int] = set()
    for entry in schedule:
        if not isinstance(entry, dict):
            raise ValueError("hours.schedule must be a list of objects")
        days = entry.get("days")
        opening = entry.get("open")
        closing = entry.get("close")
        if (
            not isinstance(days, list)
            or not days
            or any(
                isinstance(day, bool) or not isinstance(day, int) or not 1 <= day <= 7
                for day in days
            )
        ):
            raise ValueError("hours.schedule days must be weekdays from 1 to 7")
        if len(set(days)) != len(days) or seen_days.intersection(days):
            raise ValueError("hours.schedule weekdays must not repeat")
        seen_days.update(days)
        if (
            not isinstance(opening, str)
            or not isinstance(closing, str)
            or len(opening) != 5
            or len(closing) != 5
            or opening[2] != ":"
            or closing[2] != ":"
        ):
            raise ValueError("hours.schedule times must use HH:MM")
        try:
            open_time = datetime.strptime(opening, "%H:%M").time()
            close_time = datetime.strptime(closing, "%H:%M").time()
        except ValueError:
            raise ValueError("hours.schedule times must use HH:MM")
        if open_time >= close_time:
            raise ValueError("hours.schedule open must be before close")


# --- S12/S13: editable prompts and the version surface -----------------------
#
# Version history is the append-only audit trail every settings write already
# produces (`settings.change` / `settings.reset` carry the full value in
# `before`/`after`). No second table, no pointer: the KV row is the live state
# and the audit log is the history of that state, so they cannot disagree.


def _validate_persona_text(text: Any, field: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"persona.texts[{field!r}] must be non-empty text")
    if len(text) > PERSONA_TEXT_MAX_CHARS:
        raise ValueError(
            f"persona.texts[{field!r}] exceeds {PERSONA_TEXT_MAX_CHARS} characters"
        )
    if "{{" in text or "}}" in text:
        # Personas are loaded verbatim and never rendered, so ANY mustache would
        # reach the model literally. Matching only `{{word}}` would leave
        # `{{nombre del cliente}}`, `{{}}` or an unclosed `{{ nombre` through,
        # which is the same contract break.
        raise ValueError(
            f"persona.texts[{field!r}] must not contain '{{{{' or '}}}}': personas are used verbatim"
        )
    return text


def validate_persona_texts(value: Any) -> dict[str, str]:
    """Validate the editable persona before persistence (S12).

    Both prompt files are one unit: the brief is appended to the persona, so a
    partial map would silently pair an edited persona with the shipped brief.
    """
    if not isinstance(value, dict):
        raise ValueError("persona.texts must be an object")
    unknown = [key for key in value if key not in PERSONA_PROMPT_KEYS]
    if unknown:
        raise ValueError(f"persona.texts has unknown keys: {unknown}")
    return {key: _validate_persona_text(value.get(key), key) for key in PERSONA_PROMPT_KEYS}


def validate_emergency_protocol(value: Any) -> dict[str, Any]:
    """Validate the editable safety protocol before persistence (S13)."""
    if not isinstance(value, dict):
        raise ValueError("emergency.protocol must be an object")
    unknown = [field for field in value if field not in EMERGENCY_PROTOCOL_FIELDS]
    if unknown:
        raise ValueError(f"emergency.protocol has unknown fields: {unknown}")
    protocol: dict[str, Any] = {}
    for field in EMERGENCY_PROTOCOL_FIELDS:
        raw = value.get(field)
        if field in EMERGENCY_PROTOCOL_LISTS:
            if not isinstance(raw, list) or not raw:
                raise ValueError(f"emergency.protocol[{field!r}] must be a non-empty list")
            if any(not isinstance(item, str) or not item.strip() for item in raw):
                raise ValueError(
                    f"emergency.protocol[{field!r}] items must be non-empty text"
                )
            protocol[field] = [item.strip() for item in raw]
            continue
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError(f"emergency.protocol[{field!r}] must be non-empty text")
        protocol[field] = raw.strip()
    return protocol


def get_persona_texts(session: Session) -> dict[str, str]:
    """The stored persona override per prompt key; `{}` means "use the files".

    A partial or malformed stored map is treated as unset: it can only come from
    a manual DB edit, and a half-applied persona is worse than the shipped one.
    """
    stored = get_setting(session, PERSONA_TEXTS_KEY, default={})
    if not isinstance(stored, dict):
        return {}
    texts = {key: stored.get(key) for key in PERSONA_PROMPT_KEYS}
    if any(not isinstance(text, str) or not text.strip() for text in texts.values()):
        return {}
    return texts  # type: ignore[return-value]


def get_emergency_protocol(session: Session) -> dict[str, Any]:
    """The stored safety protocol, else the built-in defaults (S13).

    The emergency node reads its content here, but it never gates on this row:
    the determinism of the gate lives in `emergency_gate` + `emergency.keywords`.
    """
    stored = get_setting(session, EMERGENCY_PROTOCOL_KEY, default=None)
    if isinstance(stored, dict):
        try:
            return validate_emergency_protocol(stored)
        except ValueError:
            logger.warning(
                "emergency.protocol stored value is invalid; using the built-in protocol"
            )
    return {
        "safety_instructions": DEFAULT_SAFETY_INSTRUCTIONS,
        "contacts": DEFAULT_EMERGENCY_CONTACTS,
        "notify_message": DEFAULT_EMERGENCY_NOTIFY_MESSAGE,
    }


def delete_setting(session: Session, key: str, *, actor: str = "system") -> bool:
    """Delete one KV row so the built-in default applies again, audited.

    Deleting (instead of writing a copy of the shipped text) is what makes
    "restore default" track future releases. The caller commits.
    """
    row = session.get(Settings, key)
    if row is None:
        return False
    before = row.value
    session.delete(row)
    record_audit(
        session,
        actor=actor,
        action="settings.reset",
        entity="settings",
        entity_id=key,
        before={"value": before},
    )
    return True


def setting_versions(session: Session, key: str) -> list[dict[str, Any]]:
    """Every audited state of one setting, oldest first (version 1..N).

    A reset state has `content=None` and means "no row: the built-in default".
    """
    entries = list(
        session.scalars(
            select(AuditLog)
            .where(
                AuditLog.entity == "settings",
                AuditLog.entity_id == key,
                AuditLog.action.in_(("settings.change", "settings.reset")),
            )
            .order_by(AuditLog.id.asc())
        )
    )
    return [
        {
            "version": version,
            "created_at": entry.created_at,
            "actor": entry.actor,
            "content": None if entry.after is None else entry.after.get("value"),
        }
        for version, entry in enumerate(entries, start=1)
    ]


def setting_version_content(session: Session, key: str, version: int) -> Any:
    """Content of one version; version ``0`` is the built-in default (`None`).

    Raises `KeyError` for a version that was never recorded.
    """
    if version == 0:
        return None
    for entry in setting_versions(session, key):
        if entry["version"] == version:
            return entry["content"]
    raise KeyError(version)
