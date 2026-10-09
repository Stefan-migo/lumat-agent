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


@pytest.fixture(autouse=True)
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
    }
    assert len(recipes.RECIPES) == len({r.recipe_id for r in recipes.RECIPES.values()})


def test_install_update_enable_and_lookup(migrated_db):
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


def test_assistant_install_requires_executor_origin(migrated_db):
    with SessionLocal() as session:
        with pytest.raises(PermissionError):
            install(session, SYNTHETIC.recipe_id, {"channel": "email"}, actor="assistant")
        assert install(session, SYNTHETIC.recipe_id, {"channel": "email"}, actor="assistant", executor_origin=True)
