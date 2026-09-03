from datetime import datetime, timezone

import pytest

from app.services.calendar import build_ics, calendar_uid, idempotency_key
from app.services.templates import (
    MissingTemplateVariable,
    TemplatePolicyError,
    render_content,
    validate_channel_policy,
)


def test_calendar_identity_and_ics_preserve_timezone_and_cancelled_state():
    starts = datetime(2026, 7, 15, 14, 0, tzinfo=timezone.utc)
    ends = datetime(2026, 7, 15, 15, 0, tzinfo=timezone.utc)

    assert calendar_uid(42) == calendar_uid(42)
    assert idempotency_key(42) == idempotency_key(42)
    ics = build_ics(
        uid=calendar_uid(42),
        service="Boiler repair",
        starts_at=starts,
        ends_at=ends,
        timezone_name="America/Santiago",
        cancelled=True,
    )

    assert "UID:appointment-42@lumat.local" in ics
    assert "DTSTART;TZID=America/Santiago:20260715T100000" in ics
    assert "STATUS:CANCELLED" in ics


def test_template_rendering_rejects_missing_variables_and_channel_policy():
    with pytest.raises(MissingTemplateVariable, match="customer_name"):
        render_content("Hello {customer_name}", {})

    with pytest.raises(TemplatePolicyError, match="approved"):
        validate_channel_policy(channel="whatsapp", approved=False, business_initiated=True)

    assert render_content("Hello {customer_name}", {"customer_name": "Ana"}) == "Hello Ana"
