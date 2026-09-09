from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AutomationRule, User
from app.panel.api.deps import require_admin_json, require_user_json
from app.panel.api.serializers import to_automation_rule_dict
from app.panel.deps import get_db
from app.services import automation

router = APIRouter(tags=["panel-api-automation-rules"])


class RuleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    event_type: str
    conditions: dict[str, object]
    channel: str
    template_event: str
    cooldown_seconds: int


class RulePatch(RuleBody):
    pass


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="automation rule not found")


def _validation(error: automation.RuleValidationError) -> HTTPException:
    return HTTPException(status_code=422, detail={"field": error.field, "detail": error.detail})


def _get_rule(session: Session, rule_id: int) -> AutomationRule:
    rule = session.get(AutomationRule, rule_id)
    if rule is None:
        raise _not_found()
    return rule


@router.get("/automation-rules")
def list_rules(session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    rules = session.scalars(select(AutomationRule).order_by(AutomationRule.id.asc())).all()
    return {"rules": [to_automation_rule_dict(rule) for rule in rules]}


@router.post("/automation-rules", status_code=status.HTTP_201_CREATED)
def create_rule(body: RuleBody, session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    try:
        rule = automation.create_rule(session, body.model_dump(), actor=current.username)
    except automation.RuleValidationError as error:
        raise _validation(error)
    session.commit()
    return {"rule": to_automation_rule_dict(rule)}


@router.get("/automation-rules/{rule_id}")
def get_rule(rule_id: int, session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    return {"rule": to_automation_rule_dict(_get_rule(session, rule_id))}


@router.patch("/automation-rules/{rule_id}")
def update_rule(rule_id: int, body: RulePatch, session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    rule = _get_rule(session, rule_id)
    try:
        automation.update_rule(session, rule, body.model_dump(), actor=current.username)
    except automation.RuleValidationError as error:
        raise _validation(error)
    session.commit()
    return {"rule": to_automation_rule_dict(rule)}


def _status(rule_id: int, enabled: bool, session: Session, current: User) -> dict:
    rule = _get_rule(session, rule_id)
    automation.set_rule_enabled(session, rule, enabled, actor=current.username)
    session.commit()
    return {"ok": True, "rule": to_automation_rule_dict(rule)}


@router.post("/automation-rules/{rule_id}/enable")
def enable_rule(rule_id: int, session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    return _status(rule_id, True, session, current)


@router.post("/automation-rules/{rule_id}/disable")
def disable_rule(rule_id: int, session: Session = Depends(get_db), current: User = Depends(require_admin_json)) -> dict:
    return _status(rule_id, False, session, current)
