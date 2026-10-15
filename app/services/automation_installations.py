"""Persistence and compilation of installed automation recipes."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AutomationExecution, AutomationInstallation, AutomationRule
from app.services.audit import record_audit
from app.services.recipes import get_recipe


class RecipeAlreadyInstalled(ValueError):
    """Raised when the catalog recipe already has a persisted installation."""


def installation_snapshot(installation: AutomationInstallation) -> dict:
    return {
        "id": installation.id,
        "recipe_id": installation.recipe_id,
        "parameters": installation.parameters or {},
        "enabled": installation.enabled,
        "created_by": installation.created_by,
        "created_at": installation.created_at.isoformat() if installation.created_at else None,
        "updated_at": installation.updated_at.isoformat() if installation.updated_at else None,
    }


def _compile(session: Session, installation: AutomationInstallation, actor: str) -> AutomationRule:
    recipe = get_recipe(installation.recipe_id)
    fields = recipe.compile_rule_fields(installation.parameters or {})
    rule = session.scalar(select(AutomationRule).where(AutomationRule.installation_id == installation.id))
    if rule is None:
        rule = AutomationRule(
            name=recipe.name,
            **fields,
            enabled=installation.enabled,
            created_by=actor,
            installation_id=installation.id,
        )
        session.add(rule)
    else:
        rule.name = recipe.name
        for key, value in fields.items():
            setattr(rule, key, value)
        rule.enabled = installation.enabled
    return rule


def install(
    session: Session,
    recipe_id: str,
    parameters: dict,
    *,
    actor: str,
    executor_origin: bool = False,
    enabled: bool = False,
) -> AutomationInstallation:
    if actor == "assistant" and not executor_origin:
        raise PermissionError("assistant installations must originate from the approved tool executor")
    recipe = get_recipe(recipe_id)
    if recipe is None:
        raise ValueError("unknown recipe")
    if session.scalar(select(AutomationInstallation).where(AutomationInstallation.recipe_id == recipe_id)) is not None:
        raise RecipeAlreadyInstalled("recipe already installed")
    validated = recipe.validate_parameters(parameters)
    installation = AutomationInstallation(recipe_id=recipe_id, parameters=validated, enabled=enabled, created_by=actor)
    session.add(installation)
    session.flush()
    _compile(session, installation, actor)
    session.flush()
    record_audit(session, actor=actor, action="automation.installation.create", entity="automation_installation", entity_id=str(installation.id), after=installation_snapshot(installation))
    return installation


def update_parameters(session: Session, installation: AutomationInstallation, parameters: dict, *, actor: str) -> AutomationInstallation:
    before = installation_snapshot(installation)
    recipe = get_recipe(installation.recipe_id)
    if recipe is None:
        raise ValueError("unknown recipe")
    installation.parameters = recipe.validate_parameters(parameters)
    _compile(session, installation, actor)
    session.flush()
    record_audit(session, actor=actor, action="automation.installation.update", entity="automation_installation", entity_id=str(installation.id), before=before, after=installation_snapshot(installation))
    return installation


def set_enabled(session: Session, installation: AutomationInstallation, enabled: bool, *, actor: str) -> AutomationInstallation:
    before = installation_snapshot(installation)
    installation.enabled = enabled
    _compile(session, installation, actor)
    session.flush()
    action = "automation.installation.enable" if enabled else "automation.installation.disable"
    record_audit(session, actor=actor, action=action, entity="automation_installation", entity_id=str(installation.id), before=before, after=installation_snapshot(installation))
    return installation


def get_installation(session: Session, installation_id: int) -> AutomationInstallation | None:
    return session.get(AutomationInstallation, installation_id)


def list_installations(session: Session) -> list[AutomationInstallation]:
    return list(session.scalars(select(AutomationInstallation).order_by(AutomationInstallation.id)))


def uninstall(session: Session, installation: AutomationInstallation, *, actor: str) -> None:
    """Remove an installation together with its compiled rule and that rule's history."""
    before = installation_snapshot(installation)
    installation_id = installation.id
    rule = session.scalar(select(AutomationRule).where(AutomationRule.installation_id == installation_id))
    if rule is not None:
        session.execute(delete(AutomationExecution).where(AutomationExecution.rule_id == rule.id))
        session.delete(rule)
        session.flush()
    session.delete(installation)
    session.flush()
    record_audit(session, actor=actor, action="automation.installation.delete", entity="automation_installation", entity_id=str(installation_id), before=before)
