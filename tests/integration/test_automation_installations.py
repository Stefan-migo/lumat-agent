import pytest
from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditLog, AutomationInstallation, AutomationRule
from app.services import recipes
from app.services.automation_installations import (
    get_installation,
    install,
    list_installations,
    set_enabled,
    update_parameters,
)


SYNTHETIC = recipes.RecipeDefinition(
    recipe_id="test.synthetic",
    name="Aviso de prueba",
    description="Receta sintética para pruebas",
    category="operacion",
    trigger_kind="event",
    event_type="case.created",
    channel_allowed=frozenset({"email"}),
    parameters=(
        recipes.RecipeParameter("channel", "Canal", "channel", True),
        recipes.RecipeParameter("locale", "Idioma", "string", False, "es-CL"),
    ),
    cooldown_seconds=60,
)


@pytest.fixture()
def synthetic_recipe(monkeypatch):
    monkeypatch.setitem(recipes.RECIPES, SYNTHETIC.recipe_id, SYNTHETIC)


def test_recipe_catalog_compiles_and_validates_parameters():
    with pytest.raises(ValueError, match="unknown"):
        SYNTHETIC.validate_parameters({"channel": "email", "extra": 1})
    with pytest.raises(ValueError, match="required"):
        SYNTHETIC.validate_parameters({})
    with pytest.raises(ValueError, match="channel"):
        SYNTHETIC.validate_parameters({"channel": "whatsapp"})
    parameters = SYNTHETIC.validate_parameters({"channel": "email"})
    assert parameters == {"channel": "email", "locale": "es-CL"}
    fields = SYNTHETIC.compile_rule_fields(parameters)
    assert fields == {
        "event_type": "case.created", "conditions": {}, "channel": "email",
        "template_event": "case.created", "cooldown_seconds": 60,
        "recipient_target": "customer", "content": "",
    }
    assert len(recipes.RECIPES) == len({r.recipe_id for r in recipes.RECIPES.values()})


def test_catalog_has_compilable_recipes_with_unique_ids():
    assert len(recipes.RECIPES) == 7
    assert len(recipes.RECIPES) == len({recipe.recipe_id for recipe in recipes.RECIPES.values()})
    for recipe in recipes.RECIPES.values():
        assert recipe.trigger_kind in {"event", "offset"}
        assert any(parameter.key == "channel" for parameter in recipe.parameters)
        fields = recipe.compile_rule_fields({"channel": next(iter(recipe.channel_allowed))})
        assert fields["event_type"] == recipe.event_type


@pytest.mark.parametrize(
    ("recipe_id", "trigger_event", "parameter_key", "default"),
    [
        ("appointment_review_request", "appointment.review_due", "days_after", 3),
        ("customer_maintenance", "customer.maintenance_due", "months", 6),
    ],
)
def test_offset_recipe_catalog_and_compilation(recipe_id, trigger_event, parameter_key, default):
    recipe = recipes.get_recipe(recipe_id)
    assert recipe is not None
    assert recipe.trigger_kind == "offset"
    assert any(parameter.key == "channel" for parameter in recipe.parameters)
    numeric = next(parameter for parameter in recipe.parameters if parameter.key == parameter_key)
    assert numeric.type == "number" and numeric.default == default
    fields = recipe.compile_rule_fields({"channel": "whatsapp"})
    assert fields["event_type"] == trigger_event
    assert fields["template_event"] == trigger_event
    assert fields["channel"] == "whatsapp"


@pytest.mark.parametrize("value", ["3", 3.0, True, 0, -1])
def test_numeric_recipe_parameter_rejects_invalid_values(value):
    recipe = recipes.get_recipe("appointment_review_request")
    with pytest.raises(ValueError, match="parameter days_after must be a positive integer"):
        recipe.validate_parameters({"channel": "whatsapp", "days_after": value})


def test_numeric_recipe_parameter_applies_default_when_omitted():
    recipe = recipes.get_recipe("appointment_review_request")
    assert recipe.validate_parameters({"channel": "whatsapp"})["days_after"] == 3


def test_compile_without_channel_parameter_raises_clear_error():
    recipe = recipes.RecipeDefinition(
        recipe_id="test.no-channel", name="No channel", description="", category="operacion",
        trigger_kind="event", event_type="case.created", channel_allowed=frozenset({"email"}), parameters=(),
    )
    with pytest.raises(ValueError, match="recipe has no channel parameter"):
        recipe.compile_rule_fields({})


def test_compile_rejects_unsupported_recipient_target():
    recipe = recipes.RecipeDefinition(
        recipe_id="test.invalid-target", name="Invalid target", description="", category="operacion",
        trigger_kind="event", event_type="case.created", channel_allowed=frozenset({"email"}),
        parameters=(recipes.RecipeParameter("channel", "Canal", "channel", True),),
        recipient_target="unknown",
    )
    with pytest.raises(ValueError, match="unsupported recipient target"):
        recipe.compile_rule_fields({"channel": "email"})


def test_install_update_enable_and_lookup(migrated_db, synthetic_recipe):
    with SessionLocal() as session:
        with pytest.raises(ValueError, match="unknown recipe"):
            install(session, "missing", {}, actor="admin")
        installation = install(session, SYNTHETIC.recipe_id, {"channel": "email"}, actor="admin")
        rule = session.scalar(select(AutomationRule).where(AutomationRule.installation_id == installation.id))
        assert rule.event_type == "case.created"
        assert rule.conditions == {} and rule.channel == "email"
        assert rule.template_event == "case.created" and rule.cooldown_seconds == 60
        assert rule.enabled is installation.enabled is False
        with pytest.raises(ValueError, match="already installed"):
            install(session, SYNTHETIC.recipe_id, {"channel": "email"}, actor="admin")
        update_parameters(session, installation, {"channel": "email", "locale": "es"}, actor="admin")
        assert installation.parameters["locale"] == "es"
        assert rule.channel == "email"
        set_enabled(session, installation, True, actor="admin")
        assert installation.enabled and rule.enabled
        assert get_installation(session, installation.id) is installation
        assert list_installations(session) == [installation]
        session.flush()  # the audit trail is caller-flushed (autoflush is off)
        actions = session.scalars(select(AuditLog.action).where(AuditLog.action.like("automation.installation.%"))).all()
        assert set(actions) == {"automation.installation.create", "automation.installation.update", "automation.installation.enable"}
        session.commit()


def test_install_appointment_confirmation_compiles_content_and_recipient_target(migrated_db):
    recipe = recipes.get_recipe("appointment_confirmation")
    with SessionLocal() as session:
        installation = install(session, recipe.recipe_id, {"channel": "whatsapp"}, actor="admin")
        rule = session.scalar(select(AutomationRule).where(AutomationRule.installation_id == installation.id))
        assert (rule.event_type, rule.channel, rule.recipient_target, rule.content) == (
            "appointment.booked", "whatsapp", "customer", recipe.content,
        )


def test_assistant_install_requires_executor_origin(migrated_db, synthetic_recipe):
    with SessionLocal() as session:
        with pytest.raises(PermissionError):
            install(session, SYNTHETIC.recipe_id, {"channel": "email"}, actor="assistant")
        assert install(session, SYNTHETIC.recipe_id, {"channel": "email"}, actor="assistant", executor_origin=True)
