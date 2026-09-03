"""Authenticated calendar synchronization and template actions (AP-10/11)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.panel.api.deps import require_user_json
from app.panel.api.serializers import to_calendar_dict, to_template_dict
from app.panel.deps import get_db
from app.services import calendar, templates
from app.services.audit import record_audit

router = APIRouter(tags=["panel-api-calendar-templates"])


class TemplateBody(BaseModel):
    event: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    locale: str = Field(min_length=1)
    content: str = Field(min_length=1)
    required_variables: list[str] = Field(default_factory=list)
    approved: bool = False
    smtp_allowed: bool = True


class RenderBody(BaseModel):
    variables: dict = Field(default_factory=dict)
    business_initiated: bool = False


@router.post("/appointments/{appointment_id}/calendar/sync")
def sync_calendar(appointment_id: int, session: Session = Depends(get_db), current: User = Depends(require_user_json)) -> dict:
    appointment = session.get(calendar.Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=404, detail="appointment not found")
    sync = calendar.synchronize(session, appointment, provider=calendar.ICSProvider(), actor=current.username)
    session.commit()
    return {"ok": sync.status == "synced", "calendar": to_calendar_dict(sync)}


@router.post("/templates")
def publish_template(body: TemplateBody, session: Session = Depends(get_db), current: User = Depends(require_user_json)) -> dict:
    template = templates.publish(session, event=body.event, channel=body.channel, locale=body.locale,
                                 content=body.content, required_variables=body.required_variables,
                                 approved=body.approved, smtp_allowed=body.smtp_allowed, actor=current.username)
    session.commit()
    return {"ok": True, "template": to_template_dict(template)}


@router.get("/templates")
def list_templates(session: Session = Depends(get_db), current: User = Depends(require_user_json)) -> dict:
    rows = session.scalars(select(templates.NotificationTemplateVersion).order_by(
        templates.NotificationTemplateVersion.event,
        templates.NotificationTemplateVersion.channel,
        templates.NotificationTemplateVersion.locale,
        templates.NotificationTemplateVersion.version.desc(),
    )).all()
    return {"templates": [to_template_dict(row) for row in rows]}


@router.post("/templates/{template_id}/render")
def render_template(template_id: int, body: RenderBody, session: Session = Depends(get_db), current: User = Depends(require_user_json)) -> dict:
    try:
        rendered = templates.render(session, template_id, body.variables,
                                    business_initiated=body.business_initiated, actor=current.username)
    except templates.MissingTemplateVariable as exc:
        raise HTTPException(status_code=422, detail={"code": "missing_template_variable", "message": str(exc)}) from exc
    except templates.TemplatePolicyError as exc:
        session.commit()
        raise HTTPException(status_code=409, detail={"code": "template_policy_rejected", "message": str(exc)}) from exc
    record_audit(session, actor=current.username, action="template.rendered", entity="notification_template", entity_id=str(template_id), after={"version": rendered.template_version})
    session.commit()
    return {"ok": True, "rendered": {"content": rendered.content, "template_version": rendered.template_version, "template_id": rendered.template_id}}
