"""Immutable notification template publication, policy, and rendering."""

from __future__ import annotations

from dataclasses import dataclass
from string import Formatter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import NotificationTemplateVersion
from app.services.audit import record_audit


class MissingTemplateVariable(ValueError):
    pass


class TemplatePolicyError(ValueError):
    pass


@dataclass(frozen=True)
class RenderedTemplate:
    content: str
    template_version: int
    template_id: int


def render_content(content: str, variables: dict) -> str:
    required = {name for _, name, _, _ in Formatter().parse(content) if name}
    missing = sorted(required - variables.keys())
    if missing:
        raise MissingTemplateVariable(f"missing template variables: {', '.join(missing)}")
    return content.format(**variables)


def validate_channel_policy(*, channel: str, approved: bool, business_initiated: bool, smtp_allowed: bool = True) -> None:
    if channel == "whatsapp" and business_initiated and not approved:
        raise TemplatePolicyError("WhatsApp template must be approved")
    if channel == "smtp" and not smtp_allowed:
        raise TemplatePolicyError("SMTP policy does not allow this template")


def publish(session: Session, *, event: str, channel: str, locale: str, content: str,
            required_variables: list[str], approved: bool, actor: str, smtp_allowed: bool = True) -> NotificationTemplateVersion:
    current = session.scalar(select(func.max(NotificationTemplateVersion.version)).where(
        NotificationTemplateVersion.event == event, NotificationTemplateVersion.channel == channel,
        NotificationTemplateVersion.locale == locale,
    )) or 0
    template = NotificationTemplateVersion(event=event, channel=channel, locale=locale, version=current + 1,
                                            content=content, required_variables=required_variables,
                                            approved=approved, smtp_allowed=smtp_allowed, created_by=actor)
    session.add(template)
    session.flush()
    record_audit(session, actor=actor, action="template.published", entity="notification_template", entity_id=str(template.id), after={"version": template.version})
    return template


def render(session: Session, template_id: int, variables: dict, *, business_initiated: bool = False, actor: str | None = None) -> RenderedTemplate:
    template = session.get(NotificationTemplateVersion, template_id)
    if template is None:
        raise TemplatePolicyError("template version not found")
    try:
        validate_channel_policy(channel=template.channel, approved=template.approved,
                                business_initiated=business_initiated, smtp_allowed=template.smtp_allowed)
        missing = sorted(set(template.required_variables) - variables.keys())
        if missing:
            raise MissingTemplateVariable(f"missing template variables: {', '.join(missing)}")
        result = render_content(template.content, variables)
    except TemplatePolicyError as exc:
        if actor and template.channel == "whatsapp":
            record_audit(session, actor=actor, action="template.policy_rejected", entity="notification_template", entity_id=str(template.id), after={"reason": str(exc)})
        raise
    return RenderedTemplate(result, template.version, template.id)
