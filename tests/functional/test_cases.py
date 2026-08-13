"""Cases panel view (T5.3; HH-4, AP-5, EM-4 ack).

Functional suite: the pending/escalated cases list (HH-4), case state change
+ responsible assignment with audit (AP-5), and the emergency ack button
(EM-4) that reuses the T4.3 ack columns/audit path (acknowledged_at/ack_by —
same mechanism as the reply-keyword ack, driven by the panel instead).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.db import SessionLocal  # noqa: E402
from app.models import AuditLog, Case, Conversation, ConversationState, Customer  # noqa: E402
from app.services.users import hash_password  # noqa: E402


def _seed_case(
    *,
    phone: str = "+56911112222",
    service: str = "calefont",
    status: str = "escalado",
    emergency: bool = False,
    acknowledged: bool = False,
) -> int:
    """Create customer + conversation + one case; returns the case id."""
    with SessionLocal() as session:
        customer = Customer(phone_e164=phone, name="Ana Martínez")
        session.add(customer)
        session.flush()
        conversation = Conversation(
            customer_id=customer.id, wa_phone=phone, state=ConversationState.HUMAN
        )
        session.add(conversation)
        session.flush()
        case = Case(
            conversation_id=conversation.id,
            customer_id=customer.id,
            service=service,
            status=status,
            emergency=emergency,
            summary="needs a technician",
            acknowledged_at=datetime.now(timezone.utc) if acknowledged else None,
        )
        session.add(case)
        session.flush()
        case_id = case.id
        session.commit()
        return case_id


def _login_oper(client, make_user) -> int:
    """Create the operador (once) and log in; returns the user id."""
    operator_id = make_user("oper", "oper-pass", role="operador")
    client.post(
        "/panel/login",
        data={"username": "oper", "password": "oper-pass"},
        follow_redirects=False,
    )
    return operator_id


# ---------------------------------------------------------------------------
# HH-4 — pending/escalated cases list
# ---------------------------------------------------------------------------


@pytest.mark.spec("HH-4")
def test_cases_list_shows_customer_summary_status(client, make_user):
    _seed_case(service="calefont", status="escalado")
    _login_oper(client, make_user)

    resp = client.get("/panel/cases")

    assert resp.status_code == 200
    assert "Ana Martínez" in resp.text
    assert "needs a technician" in resp.text
    assert "escalado" in resp.text


@pytest.mark.spec("HH-4")
def test_cases_list_excludes_closed_cases(client, make_user):
    _seed_case(status="escalado")
    open_id = _seed_case(phone="+56933334444", status="abierto")
    _login_oper(client, make_user)
    from datetime import datetime, timezone

    with SessionLocal() as session:
        case = session.get(Case, open_id)
        case.closed_at = datetime.now(timezone.utc)
        case.status = "cerrado"
        session.commit()

    resp = client.get("/panel/cases")

    assert resp.status_code == 200
    assert "needs a technician" in resp.text  # still one open case
    # Only ONE case row is rendered (the closed one is filtered out).
    assert resp.text.count("needs a technician") == 1


# ---------------------------------------------------------------------------
# AP-5 — state change + responsible assignment (audited)
# ---------------------------------------------------------------------------


@pytest.mark.spec("AP-5")
def test_case_update_status_and_responsible_audited(client, make_user):
    case_id = _seed_case(status="abierto")
    operator_id = _login_oper(client, make_user)

    resp = client.post(
        f"/panel/cases/{case_id}/update",
        data={"status": "escalado", "responsible_id": str(operator_id)},
        follow_redirects=True,
    )

    assert resp.status_code == 200
    with SessionLocal() as session:
        case = session.get(Case, case_id)
        assert case.status == "escalado"
        assert case.responsible_id == operator_id
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "case.updated")
        )
        assert audit is not None
        assert audit.actor == "oper"
        assert audit.before == {"status": "abierto", "responsible_id": None}
        assert audit.after == {"status": "escalado", "responsible_id": operator_id}


@pytest.mark.spec("AP-5")
def test_case_update_clears_responsible(client, make_user):
    operator_id = _login_oper(client, make_user)
    case_id = _seed_case(status="abierto")
    with SessionLocal() as session:
        case = session.get(Case, case_id)
        case.responsible_id = operator_id
        session.commit()

    resp = client.post(
        f"/panel/cases/{case_id}/update",
        data={"status": "abierto", "responsible_id": ""},
        follow_redirects=True,
    )

    assert resp.status_code == 200
    with SessionLocal() as session:
        case = session.get(Case, case_id)
        assert case.responsible_id is None
        assert case.status == "abierto"


# ---------------------------------------------------------------------------
# EM-4 — emergency flag + ack button
# ---------------------------------------------------------------------------


@pytest.mark.spec("EM-4")
def test_emergency_case_shows_flag_and_ack_button(client, make_user):
    _seed_case(emergency=True, acknowledged=False)
    _login_oper(client, make_user)

    resp = client.get("/panel/cases")

    assert resp.status_code == 200
    assert "emergency" in resp.text.lower() or "ack" in resp.text.lower()
    assert "Acknowledge" in resp.text


@pytest.mark.spec("EM-4")
def test_ack_button_records_ack_and_audits(client, make_user):
    case_id = _seed_case(emergency=True, acknowledged=False)
    _login_oper(client, make_user)

    resp = client.post(f"/panel/cases/{case_id}/ack", follow_redirects=True)

    assert resp.status_code == 200
    with SessionLocal() as session:
        case = session.get(Case, case_id)
        assert case.acknowledged_at is not None
        assert case.ack_by == "oper"
        audit = session.scalar(
            select(AuditLog).where(AuditLog.action == "case.acknowledged")
        )
        assert audit is not None
        assert audit.actor == "oper"
        assert audit.after["ack_by"] == "oper"


@pytest.mark.spec("EM-4")
def test_ack_button_hidden_after_ack(client, make_user):
    _seed_case(emergency=True, acknowledged=True)
    _login_oper(client, make_user)

    resp = client.get("/panel/cases")

    assert resp.status_code == 200
    assert "acknowledged" in resp.text.lower()
    assert "Acknowledge" not in resp.text


# ---------------------------------------------------------------------------
# Auth — cases routes require login
# ---------------------------------------------------------------------------


@pytest.mark.spec("AP-2")
def test_cases_routes_require_login(client):
    resp = client.get("/panel/cases", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/panel/login"

    resp = client.post(
        "/panel/cases/1/update", data={"status": "x"}, follow_redirects=False
    )
    assert resp.status_code == 302

    resp = client.post("/panel/cases/1/ack", follow_redirects=False)
    assert resp.status_code == 302
