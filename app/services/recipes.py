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
        fields = {
            "event_type": self.event_type,
            "conditions": {},
            "channel": values["channel"],
            "template_event": self.event_type,
            "cooldown_seconds": self.cooldown_seconds,
        }
        if fields["channel"] not in ALLOWED_CHANNELS:
            raise ValueError("unsupported channel")
        return fields


RECIPES: dict[str, RecipeDefinition] = {}


def get_recipe(recipe_id: str) -> RecipeDefinition | None:
    return RECIPES.get(recipe_id)
