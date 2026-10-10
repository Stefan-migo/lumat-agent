"""Code-defined automation recipe catalog and rule compilation."""

from dataclasses import dataclass
import re
from typing import Any

from app.services.automation import ALLOWED_CHANNELS, ALLOWED_EVENTS

_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


@dataclass(frozen=True)
class RecipeParameter:
    key: str
    label: str
    type: str
    required: bool
    default: Any = None


@dataclass(frozen=True)
class RecipeDefinition:
    recipe_id: str
    name: str
    description: str
    category: str
    trigger_kind: str
    event_type: str | None
    channel_allowed: frozenset[str]
    parameters: tuple[RecipeParameter, ...]
    cooldown_seconds: int = 0
    recipient_target: str = "customer"
    content: str = ""

    def validate_parameters(self, values: dict) -> dict:
        if not isinstance(values, dict):
            raise ValueError("parameters must be an object")
        specs = {parameter.key: parameter for parameter in self.parameters}
        unknown = values.keys() - specs.keys()
        if unknown:
            raise ValueError(f"unknown parameter: {sorted(unknown)[0]}")
        result = {}
        for key, parameter in specs.items():
            if key in values:
                value = values[key]
            elif parameter.required and parameter.default is None:
                raise ValueError(f"parameter {key} is required")
            else:
                value = parameter.default
            if parameter.type == "channel":
                if not isinstance(value, str) or value not in self.channel_allowed or value not in ALLOWED_CHANNELS:
                    raise ValueError(f"unsupported channel for parameter {key}")
            elif parameter.type == "string" and value is not None and not isinstance(value, str):
                raise ValueError(f"parameter {key} must be a string")
            elif parameter.type == "number" and (isinstance(value, bool) or not isinstance(value, int) or value <= 0):
                raise ValueError(f"parameter {key} must be a positive integer")
            elif parameter.type == "time":
                if not isinstance(value, str) or not _TIME_RE.fullmatch(value):
                    raise ValueError(f"parameter {key} must be a HH:MM time")
            elif parameter.type == "weekday":
                if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 7:
                    raise ValueError(f"parameter {key} must be a weekday 1-7")
            result[key] = value
        return result

    def compile_rule_fields(self, parameters: dict) -> dict:
        if self.trigger_kind not in {"event", "offset", "schedule"} or self.event_type not in ALLOWED_EVENTS:
            raise ValueError("recipe event is not supported")
        values = self.validate_parameters(parameters)
        if self.recipient_target not in {"customer", "admin"}:
            raise ValueError("unsupported recipient target")
        if "channel" not in values:
            raise ValueError("recipe has no channel parameter")
        fields = {
            "event_type": self.event_type,
            "conditions": {},
            "channel": values.get("channel"),
            "template_event": self.event_type,
            "cooldown_seconds": self.cooldown_seconds,
            "recipient_target": self.recipient_target,
            "content": self.content,
        }
        if fields["channel"] not in ALLOWED_CHANNELS:
            raise ValueError("unsupported channel")
        return fields


_EVENT_CHANNEL = (RecipeParameter("channel", "Canal", "channel", True),)


def _event_recipe(
    recipe_id: str,
    name: str,
    category: str,
    event_type: str,
    recipient_target: str,
    channel_allowed: frozenset[str],
    content: str,
) -> RecipeDefinition:
    return RecipeDefinition(
        recipe_id=recipe_id,
        name=name,
        description="",
        category=category,
        trigger_kind="event",
        event_type=event_type,
        channel_allowed=channel_allowed,
        parameters=_EVENT_CHANNEL,
        cooldown_seconds=0,
        recipient_target=recipient_target,
        content=content,
    )


def _offset_recipe(
    recipe_id: str,
    name: str,
    category: str,
    trigger_event: str,
    recipient_target: str,
    channel_allowed: frozenset[str],
    content: str,
    offset_parameter: RecipeParameter,
) -> RecipeDefinition:
    return RecipeDefinition(
        recipe_id=recipe_id,
        name=name,
        description="",
        category=category,
        trigger_kind="offset",
        event_type=trigger_event,
        channel_allowed=channel_allowed,
        parameters=(RecipeParameter("channel", "Canal", "channel", True), offset_parameter),
        cooldown_seconds=0,
        recipient_target=recipient_target,
        content=content,
    )


def _schedule_recipe(
    recipe_id: str,
    name: str,
    category: str,
    trigger_event: str,
    content: str,
    schedule_parameters: tuple[RecipeParameter, ...],
) -> RecipeDefinition:
    return RecipeDefinition(
        recipe_id=recipe_id,
        name=name,
        description="",
        category=category,
        trigger_kind="schedule",
        event_type=trigger_event,
        channel_allowed=frozenset({"whatsapp", "email"}),
        parameters=(RecipeParameter("channel", "Canal", "channel", True), *schedule_parameters),
        cooldown_seconds=0,
        recipient_target="admin",
        content=content,
    )


RECIPES: dict[str, RecipeDefinition] = {
    recipe.recipe_id: recipe
    for recipe in (
        _event_recipe(
            "appointment_confirmation", "Confirmación de reserva", "reservas",
            "appointment.booked", "customer", frozenset({"whatsapp"}),
            "Tu visita en Lumat quedó registrada. Te esperamos.",
        ),
        _event_recipe(
            "appointment_cancellation", "Aviso de cancelación", "reservas",
            "appointment.cancelled", "customer", frozenset({"whatsapp"}),
            "Tu visita en Lumat fue cancelada.",
        ),
        _event_recipe(
            "appointment_rescheduled", "Reprogramación de visita", "reservas",
            "appointment.rescheduled", "customer", frozenset({"whatsapp"}),
            "Tu visita en Lumat fue reprogramada. Te contactaremos con el nuevo horario.",
        ),
        _event_recipe(
            "appointment_no_show", "Aviso de no presentación", "reservas",
            "appointment.no_show", "admin", frozenset({"whatsapp", "email"}),
            "Aviso: una visita agendada no se presentó.",
        ),
        _event_recipe(
            "case_new_request", "Nueva solicitud al equipo", "operacion",
            "case.created", "admin", frozenset({"whatsapp", "email"}),
            "Nueva solicitud de un cliente en Lumat.",
        ),
        _offset_recipe(
            "appointment_review_request", "Pedir evaluación", "postventa",
            "appointment.review_due", "customer", frozenset({"whatsapp"}),
            "¿Cómo estuvo tu visita? Nos encantaría conocer tu opinión.",
            RecipeParameter("days_after", "Días después de la visita", "number", True, 3),
        ),
        _offset_recipe(
            "customer_maintenance", "Mantención periódica", "postventa",
            "customer.maintenance_due", "customer", frozenset({"whatsapp"}),
            "Ya pasó un tiempo desde tu última mantención. ¿Agendamos una nueva visita?",
            RecipeParameter("months", "Meses desde el último servicio", "number", True, 6),
        ),
        _schedule_recipe(
            "admin_daily_summary", "Resumen diario", "resumenes",
            "admin.daily_summary_due", "",
            (RecipeParameter("time", "Hora del resumen", "time", True, "07:00"),),
        ),
        _schedule_recipe(
            "admin_weekly_summary", "Resumen semanal", "resumenes",
            "admin.weekly_summary_due", "",
            (RecipeParameter("weekday", "Día de la semana", "weekday", True, 1),
             RecipeParameter("time", "Hora del resumen", "time", True, "07:00")),
        ),
    )
}

assert all(any(parameter.key == "channel" for parameter in recipe.parameters) for recipe in RECIPES.values())


def get_recipe(recipe_id: str) -> RecipeDefinition | None:
    return RECIPES.get(recipe_id)
