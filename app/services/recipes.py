"""Code-defined automation recipe catalog and rule compilation."""

from dataclasses import dataclass
from typing import Any

from app.services.automation import ALLOWED_CHANNELS, ALLOWED_EVENTS


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
            elif parameter.required:
                raise ValueError(f"parameter {key} is required")
            else:
                value = parameter.default
            if parameter.type == "channel":
                if not isinstance(value, str) or value not in self.channel_allowed or value not in ALLOWED_CHANNELS:
                    raise ValueError(f"unsupported channel for parameter {key}")
            elif parameter.type == "string" and value is not None and not isinstance(value, str):
                raise ValueError(f"parameter {key} must be a string")
            result[key] = value
        return result

    def compile_rule_fields(self, parameters: dict) -> dict:
        if self.trigger_kind != "event" or self.event_type not in ALLOWED_EVENTS:
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
    )
}

assert all(any(parameter.key == "channel" for parameter in recipe.parameters) for recipe in RECIPES.values())


def get_recipe(recipe_id: str) -> RecipeDefinition | None:
    return RECIPES.get(recipe_id)
