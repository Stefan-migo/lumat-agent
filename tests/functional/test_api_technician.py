import json
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.db import SessionLocal
from app.models import (
    Appointment,
    AppointmentHistory,
    AppointmentStatus,
    AuditLog,
    Case,
    Conversation,
    Customer,
    NotificationOperation,
    TechnicianVisitState,
    User,
)
from app.services import scheduling, visit_actions
from app.services.settings import SETTINGS_DEFAULTS, set_setting


def _login(client, name="tech", password="tech-pass"):
    assert client.post("/panel/api/login", json={"username": name, "password": password}).status_code == 200


def _meta_template_body(router) -> dict:
    """The JSON body of the last Meta send the router intercepted."""
    return json.loads(router.calls.last.request.content)


@pytest.fixture
def recorded_sends(monkeypatch):
    """Record Meta template sends without hitting the network (never-sent proof)."""
    calls: list = []
    monkeypatch.setattr(
        "app.services.notify.send_template",
        lambda recipient, params, *, template_name: calls.append((recipient, params, template_name)) or "wamid.test",
    )
    return calls


def _appointment(technician_id, phone, day, summary, *, emergency=False, priority=None, local_time=time(10)):
    with SessionLocal() as session:
        customer = Customer(phone_e164=phone, name=f"Customer {phone[-2:]}", email="private@example.test", address="Sensitive address 42", comuna="Providencia", consent_status=True)
        session.add(customer); session.flush()
        conversation = Conversation(customer_id=customer.id, wa_phone=customer.phone_e164)
        session.add(conversation); session.flush()
        case = Case(conversation_id=conversation.id, customer_id=customer.id, service="calefont", summary=summary, status="open", emergency=emergency, priority=priority)
        session.add(case); session.flush()
        appointment = scheduling.book(session, service="calefont", customer_id=customer.id, case_id=case.id, technician_id=technician_id, local_date=day, local_time=local_time, timezone_name="America/Santiago", duration_minutes=60, actor="oper")
        session.commit()
        return appointment.id


def _open_window_appointment(technician_id, phone, *, minutes_ahead=10, local_time=time(10), day=date(2026, 6, 1)):
    """Book a visit whose quick-action window is open right now.

    The visit starts `minutes_ahead` from now, so `en_route` (T-60) and
    `arrived` (T-15) are both available and the visit is not yet closed."""
    appointment_id = _appointment(technician_id, phone, day, "quick action", local_time=local_time)
    starts = datetime.now(timezone.utc) + timedelta(minutes=minutes_ahead)
    with SessionLocal() as session:
        session.query(Appointment).filter_by(id=appointment_id).update(
            {
                "starts_at": starts,
                "ends_at": starts + timedelta(minutes=60),
                "local_start": starts.astimezone(ZoneInfo("America/Santiago")).replace(tzinfo=None),
            }
        )
        session.commit()
    return appointment_id


def _prior_send_event(appointment_id, action, age_seconds):
    """Insert the audit row a previous send would have left (app can INSERT audit_log)."""
    with SessionLocal() as session:
        session.add(
            AuditLog(
                actor="tech",
                action=action,
                entity="appointment",
                entity_id=str(appointment_id),
                created_at=datetime.now(timezone.utc) - timedelta(seconds=age_seconds),
            )
        )
        session.commit()


def _snapshot(appointment_id, action):
    """State, per-action audit rows, total audit rows and notification operations."""
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        return {
            "state": appointment.technician_state,
            "state_at": appointment.technician_state_at,
            "action_audit": session.query(AuditLog).filter_by(action=action, entity="appointment", entity_id=str(appointment_id)).count(),
            "audit_total": session.query(AuditLog).count(),
            "operations": session.query(NotificationOperation).count(),
        }


def test_technician_gets_owned_past_today_future_in_chronological_order(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    other = make_user("other-tech", "other-pass", role="tecnico")
    for index, summary in enumerate(("past", "today", "future"), 2):
        _appointment(technician, f"+5690000000{index}", date(2026, 1, index), summary)
    _appointment(other, "+56900000005", date(2026, 1, 1), "unowned")
    _login(client)
    response = client.get("/panel/api/technician/agenda")
    assert response.status_code == 200
    assert [row["case_summary"] for row in response.json()["appointments"]] == ["past", "today", "future"]


def test_technician_cannot_forge_ownership_or_receive_sensitive_fields(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    other = make_user("other-tech", "other-pass", role="tecnico")
    _appointment(other, "+56900000011", date(2026, 1, 1), "do not leak")
    _appointment(technician, "+56900000012", date(2026, 1, 2), "allowed")
    _login(client)
    response = client.get("/panel/api/technician/agenda", params={"technician_id": other, "appointment_id": 1})
    row = response.json()["appointments"][0]
    assert [row["case_summary"]] == ["allowed"]
    assert set(row) == {"id", "service", "local_start", "starts_at", "ends_at", "timezone", "status", "emergency", "priority", "customer", "case_summary"}
    assert set(row["customer"]) == {"name", "address", "comuna"}
    assert row["status"] in {"booked", "cancelled", "completed", "no_show"}
    assert row["emergency"] is False
    assert row["priority"] is None
    assert all(value not in response.text for value in ("private@example.test", "consent_status", "history", "sync", "notes", "+56900000012"))


def test_technician_receives_visit_safety_fields(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _appointment(technician, "+56900000014", date(2026, 1, 4), "emergency visit", emergency=True, priority="alta")
    _login(client)

    response = client.get("/panel/api/technician/agenda")

    assert response.status_code == 200
    row = next(item for item in response.json()["appointments"] if item["id"] == appointment_id)
    assert row["emergency"] is True
    assert row["priority"] == "alta"


def test_cancelled_appointment_stays_visible_and_marked(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _appointment(technician, "+56900000013", date(2026, 1, 3), "cancelled visit")
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        scheduling.cancel(session, appointment, actor="oper", reason="dispatch cancelled")
        session.commit()
    _login(client)
    response = client.get("/panel/api/technician/agenda")
    assert response.status_code == 200
    row = next(item for item in response.json()["appointments"] if item["id"] == appointment_id)
    assert row["status"] == "cancelled"


def test_technician_agenda_requires_authenticated_session(client):
    response = client.get("/panel/api/technician/agenda")
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_technician_reads_owned_appointment_detail_allow_list(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _appointment(technician, "+56900000021", date(2026, 1, 5), "detalle propio")
    _login(client)

    response = client.get(f"/panel/api/technician/appointments/{appointment_id}")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"appointment", "customer", "case", "quick_actions"}
    assert set(body["appointment"]) == {
        "id", "service", "customer_id", "case_id", "technician_id", "local_start",
        "timezone", "starts_at", "ends_at", "duration_minutes", "status",
        "technician_state", "technician_state_at",
    }
    assert set(body["customer"]) == {"id", "name", "address", "comuna"}
    assert set(body["case"]) == {"id", "conversation_id"}
    assert set(body["quick_actions"]) == {"en_route", "arrived"}
    assert all(set(action) == {"resend_available_at"} for action in body["quick_actions"].values())
    assert body["appointment"]["id"] == appointment_id
    assert body["appointment"]["service"] == "calefont"
    assert all(
        value not in response.text
        for value in ("private@example.test", "consent_status", "history", "sync", "notes", "phone", "conversation_summary", "+56900000021")
    )


def test_technician_detail_hides_foreign_and_unknown_appointments_as_not_found(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    other = make_user("other-tech", "other-pass", role="tecnico")
    foreign_id = _appointment(other, "+56900000031", date(2026, 1, 6), "ajena")
    _login(client)

    assert client.get(f"/panel/api/technician/appointments/{foreign_id}").status_code == 404
    assert client.get("/panel/api/technician/appointments/999999").status_code == 404


def test_technician_detail_rejects_non_technician_role(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _appointment(technician, "+56900000041", date(2026, 1, 7), "solo tecnico")
    _login(client, "oper", "oper-pass")

    assert client.get(f"/panel/api/technician/appointments/{appointment_id}").status_code == 403


def test_technician_detail_requires_authenticated_session(client):
    response = client.get("/panel/api/technician/appointments/1")
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_technician_cannot_reach_the_operator_detail_endpoint(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _appointment(technician, "+56900000051", date(2026, 1, 8), "propia")
    _login(client)

    assert client.get(f"/panel/api/appointments/{appointment_id}").status_code == 403


def test_technician_detail_exposes_visit_state_and_resend_availability(client, make_user, recorded_sends):
    """WU7: the read carries the field state and, per action, when a resend unlocks."""
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _open_window_appointment(technician, "+56900000071")
    _login(client)

    fresh = client.get(f"/panel/api/technician/appointments/{appointment_id}")
    assert fresh.status_code == 200
    body = fresh.json()
    assert body["appointment"]["technician_state"] is None
    assert body["appointment"]["technician_state_at"] is None
    assert body["quick_actions"] == {
        "en_route": {"resend_available_at": None},
        "arrived": {"resend_available_at": None},
    }

    assert client.post(f"/panel/api/technician/appointments/{appointment_id}/en_route").status_code == 200

    after = client.get(f"/panel/api/technician/appointments/{appointment_id}").json()
    assert after["appointment"]["technician_state"] == "en_route"
    assert after["appointment"]["technician_state_at"] is not None
    unlock = datetime.fromisoformat(after["quick_actions"]["en_route"]["resend_available_at"])
    assert timedelta(minutes=4) < unlock - datetime.now(timezone.utc) <= timedelta(minutes=5)
    assert after["quick_actions"]["arrived"]["resend_available_at"] is None


def test_technician_detail_resend_availability_is_read_from_the_audit_log(client, make_user):
    """WU7/S7: the cooldown surfaced on the read comes from the action's audit row."""
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _open_window_appointment(technician, "+56900000072")
    _prior_send_event(appointment_id, "appointment.en_route", age_seconds=60)
    _login(client)

    body = client.get(f"/panel/api/technician/appointments/{appointment_id}").json()

    unlock = datetime.fromisoformat(body["quick_actions"]["en_route"]["resend_available_at"])
    assert timedelta(minutes=3) < unlock - datetime.now(timezone.utc) <= timedelta(minutes=4)
    assert body["quick_actions"]["arrived"]["resend_available_at"] is None


def test_technician_detail_without_an_audit_row_surfaces_no_cooldown(client, make_user):
    """S7: the cooldown is the audit log — a state column alone is not a send."""
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _open_window_appointment(technician, "+56900000073")
    with SessionLocal() as session:
        session.query(Appointment).filter_by(id=appointment_id).update({
            "technician_state": TechnicianVisitState.EN_ROUTE,
            "technician_state_at": datetime.now(timezone.utc),
        })
        session.commit()
    _login(client)

    body = client.get(f"/panel/api/technician/appointments/{appointment_id}").json()

    assert body["appointment"]["technician_state"] == "en_route"
    assert body["appointment"]["technician_state_at"] is not None
    assert body["quick_actions"]["en_route"]["resend_available_at"] is None


def test_operator_detail_payload_carries_the_technician_field_state(client, make_user):
    """S9: the office sees the field state the technician marked. This test used to
    pin the ABSENCE (WU7 kept the field state technician-only); WU8 inverts it. The
    privacy intent stays: the office payload still carries no phone, email or consent."""
    technician = make_user("tech", "tech-pass", role="tecnico")
    make_user("oper", "oper-pass", role="operador")
    appointment_id = _appointment(technician, "+56900000074", date(2026, 1, 10), "operador")
    _login(client, "oper", "oper-pass")

    body = client.get(f"/panel/api/appointments/{appointment_id}").json()

    assert set(body) == {"appointment", "customer", "case", "conversation_summary"}
    assert body["appointment"]["technician_state"] is None
    assert body["appointment"]["technician_state_at"] is None
    assert set(body["customer"]) == {"id", "name", "address", "comuna"}


@pytest.mark.parametrize("outcome", ["completed", "no_show"])
def test_technician_closes_own_appointment_and_it_is_audited(client, make_user, outcome):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _appointment(technician, "+56900000061", date(2026, 1, 9), "cierre propio")
    _login(client)

    response = client.post(
        f"/panel/api/technician/appointments/{appointment_id}/close",
        json={"outcome": outcome, "reason": "terminada"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    with SessionLocal() as session:
        assert session.get(Appointment, appointment_id).status.value == outcome
        history = session.query(AppointmentHistory).filter_by(appointment_id=appointment_id).order_by(AppointmentHistory.id).all()
        assert [entry.action for entry in history] == ["booked", outcome]
        assert session.query(AuditLog).filter_by(action=f"appointment.{outcome}", entity_id=str(appointment_id)).count() == 1


def test_technician_close_hides_foreign_and_unknown_appointments_as_not_found(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    other = make_user("other-tech", "other-pass", role="tecnico")
    foreign_id = _appointment(other, "+56900000071", date(2026, 1, 10), "ajena")
    _login(client)

    foreign = client.post(f"/panel/api/technician/appointments/{foreign_id}/close", json={"outcome": "completed"})
    unknown = client.post("/panel/api/technician/appointments/999999/close", json={"outcome": "completed"})

    assert foreign.status_code == 404
    assert unknown.status_code == 404
    assert foreign.text == unknown.text == '{"detail":"appointment not found"}'
    with SessionLocal() as session:
        assert session.get(Appointment, foreign_id).status is AppointmentStatus.BOOKED


def test_technician_close_rejects_non_technician_role(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _appointment(technician, "+56900000081", date(2026, 1, 11), "solo tecnico")
    _login(client, "oper", "oper-pass")

    assert client.post(f"/panel/api/technician/appointments/{appointment_id}/close", json={"outcome": "completed"}).status_code == 403


def test_technician_close_requires_authenticated_session(client):
    response = client.post("/panel/api/technician/appointments/1/close", json={"outcome": "completed"})
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_technician_close_rejects_unknown_outcome(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _appointment(technician, "+56900000091", date(2026, 1, 12), "propia")
    _login(client)

    assert client.post(f"/panel/api/technician/appointments/{appointment_id}/close", json={"outcome": "unknown"}).status_code == 422


def test_technician_close_rejects_non_booked_appointment(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _appointment(technician, "+56900000101", date(2026, 1, 13), "propia")
    with SessionLocal() as session:
        session.query(Appointment).filter_by(id=appointment_id).update({"status": AppointmentStatus.CANCELLED})
        session.commit()
    _login(client)

    refused = client.post(f"/panel/api/technician/appointments/{appointment_id}/close", json={"outcome": "no_show"})

    assert refused.status_code == 409
    assert refused.json()["detail"] == {"code": "invalid_lifecycle", "message": "only booked appointments can be closed"}


def test_technician_close_cannot_be_applied_twice(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _appointment(technician, "+56900000111", date(2026, 1, 14), "propia")
    _login(client)
    assert client.post(f"/panel/api/technician/appointments/{appointment_id}/close", json={"outcome": "no_show"}).status_code == 200
    with SessionLocal() as session:
        history_before = session.query(AppointmentHistory).filter_by(appointment_id=appointment_id).count()
        audit_before = session.query(AuditLog).filter_by(entity_id=str(appointment_id)).count()

    second = client.post(f"/panel/api/technician/appointments/{appointment_id}/close", json={"outcome": "completed"})

    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "invalid_lifecycle"
    with SessionLocal() as session:
        assert session.get(Appointment, appointment_id).status is AppointmentStatus.NO_SHOW
        assert session.query(AppointmentHistory).filter_by(appointment_id=appointment_id).count() == history_before
        assert session.query(AuditLog).filter_by(entity_id=str(appointment_id)).count() == audit_before


def test_technician_close_cannot_forge_ownership_with_a_body_field(client, make_user):
    technician = make_user("tech", "tech-pass", role="tecnico")
    other = make_user("other-tech", "other-pass", role="tecnico")
    foreign_id = _appointment(other, "+56900000121", date(2026, 1, 15), "ajena")
    _login(client)

    response = client.post(
        f"/panel/api/technician/appointments/{foreign_id}/close",
        json={"outcome": "completed", "technician_id": technician},
    )

    assert response.status_code == 404
    with SessionLocal() as session:
        assert session.get(Appointment, foreign_id).status is AppointmentStatus.BOOKED


# ---------------------------------------------------------------------------
# WU6 — WhatsApp quick actions: field state + template send + cooldown (S7, S8)
# ---------------------------------------------------------------------------


def test_visit_action_templates_are_registered_settings():
    assert SETTINGS_DEFAULTS["notify.en_route_template_name"] == "en_route"
    assert SETTINGS_DEFAULTS["notify.arrived_template_name"] == "arrived"


def test_technician_en_route_sends_the_customer_template_and_never_leaks_the_phone(client, make_user, mock_meta_send):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _open_window_appointment(technician, "+56900000401")
    _login(client)

    response = client.post(f"/panel/api/technician/appointments/{appointment_id}/en_route")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["technician_state"] == "en_route"
    assert datetime.fromisoformat(body["resend_available_at"]) > datetime.now(timezone.utc)
    # S8: the customer phone is resolved server-side and never returned.
    assert "+56900000401" not in response.text
    assert "phone" not in response.text

    sent = _meta_template_body(mock_meta_send)
    assert sent["to"] == "+56900000401"
    assert sent["type"] == "template"
    assert sent["template"]["name"] == "en_route"
    assert sent["template"]["language"]["code"] == "es"

    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        assert appointment.technician_state is TechnicianVisitState.EN_ROUTE
        assert appointment.technician_state_at is not None
        assert session.query(AuditLog).filter_by(action="appointment.en_route", entity_id=str(appointment_id)).count() == 1


def test_technician_arrived_sends_its_own_template(client, make_user, mock_meta_send):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _open_window_appointment(technician, "+56900000402")
    _login(client)

    response = client.post(f"/panel/api/technician/appointments/{appointment_id}/arrived")

    assert response.status_code == 200
    assert response.json()["technician_state"] == "arrived"
    assert "+56900000402" not in response.text
    assert _meta_template_body(mock_meta_send)["template"]["name"] == "arrived"


def test_technician_quick_action_uses_the_configured_template_name(client, make_user, mock_meta_send):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _open_window_appointment(technician, "+56900000403")
    with SessionLocal() as session:
        set_setting(session, "notify.en_route_template_name", "en_camino_aprobado")
        session.commit()
    _login(client)

    assert client.post(f"/panel/api/technician/appointments/{appointment_id}/en_route").status_code == 200

    assert _meta_template_body(mock_meta_send)["template"]["name"] == "en_camino_aprobado"


def test_technician_quick_action_sends_the_four_parameter_template_contract(client, make_user, recorded_sends):
    """Meta template contract: {{1}} customer, {{2}} technician, {{3}} date, {{4}} time."""
    named = make_user("tech", "tech-pass", role="tecnico")
    with SessionLocal() as session:
        session.query(User).filter_by(id=named).update({"name": "Pedro Soto"})
        session.commit()
    unnamed = make_user("tech2", "tech2-pass", role="tecnico")
    first = _open_window_appointment(named, "+56900000491")
    second = _open_window_appointment(unnamed, "+56900000492")
    _login(client)
    assert client.post(f"/panel/api/technician/appointments/{first}/en_route").status_code == 200
    _login(client, "tech2", "tech2-pass")
    assert client.post(f"/panel/api/technician/appointments/{second}/en_route").status_code == 200

    recipient, params, template_name = recorded_sends[0]
    assert recipient == "+56900000491"
    assert template_name == "en_route"
    assert len(params) == 4
    assert params[0] == "Customer 91"
    assert params[1] == "Pedro Soto"
    datetime.strptime(params[2], "%d/%m/%Y")
    datetime.strptime(params[3], "%H:%M")
    # A technician with no display name falls back to their login username.
    assert recorded_sends[1][1][1] == "tech2"


def test_technician_quick_action_cooldown_rejects_a_second_click(client, make_user, mock_meta_send):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _open_window_appointment(technician, "+56900000411")
    _login(client)
    assert client.post(f"/panel/api/technician/appointments/{appointment_id}/en_route").status_code == 200
    before = _snapshot(appointment_id, "appointment.en_route")

    second = client.post(f"/panel/api/technician/appointments/{appointment_id}/en_route")

    assert second.status_code == 429
    detail = second.json()["detail"]
    assert detail["code"] == "resend_cooldown"
    assert 0 < detail["retry_after_seconds"] <= 300
    assert "Retry-After" in second.headers
    # A rejected click writes nothing and never reaches Meta.
    assert len(mock_meta_send.calls) == 1
    assert _snapshot(appointment_id, "appointment.en_route") == before


def test_technician_quick_action_allows_a_resend_after_the_cooldown(client, make_user, mock_meta_send):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _open_window_appointment(technician, "+56900000421")
    _login(client)
    with SessionLocal() as session:
        session.add(
            AuditLog(
                actor="tech",
                action="appointment.en_route",
                entity="appointment",
                entity_id=str(appointment_id),
                created_at=datetime.now(timezone.utc) - timedelta(minutes=6),
            )
        )
        session.commit()

    response = client.post(f"/panel/api/technician/appointments/{appointment_id}/en_route")

    assert response.status_code == 200
    assert _meta_template_body(mock_meta_send)["template"]["name"] == "en_route"


def test_technician_quick_action_rejects_outside_the_window_and_sends_nothing(client, make_user, recorded_sends):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _open_window_appointment(technician, "+56900000431", minutes_ahead=240)
    _login(client)

    response = client.post(f"/panel/api/technician/appointments/{appointment_id}/en_route")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "visit_state_unavailable"
    assert recorded_sends == []
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        assert appointment.technician_state is None
        assert session.query(AuditLog).filter_by(action="appointment.en_route", entity_id=str(appointment_id)).count() == 0


def test_technician_quick_action_rejects_a_backwards_transition(client, make_user, mock_meta_send):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _open_window_appointment(technician, "+56900000441")
    _login(client)
    assert client.post(f"/panel/api/technician/appointments/{appointment_id}/arrived").status_code == 200

    response = client.post(f"/panel/api/technician/appointments/{appointment_id}/en_route")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "visit_state_unavailable"
    with SessionLocal() as session:
        assert session.get(Appointment, appointment_id).technician_state is TechnicianVisitState.ARRIVED


def test_technician_quick_action_hides_foreign_and_unknown_appointments_as_not_found(client, make_user, recorded_sends):
    technician = make_user("tech", "tech-pass", role="tecnico")
    other = make_user("other-tech", "other-pass", role="tecnico")
    foreign_id = _open_window_appointment(other, "+56900000451")
    _login(client)

    foreign = client.post(f"/panel/api/technician/appointments/{foreign_id}/en_route")
    unknown = client.post("/panel/api/technician/appointments/999999/en_route")

    assert foreign.status_code == 404
    assert unknown.status_code == 404
    assert foreign.text == unknown.text == '{"detail":"appointment not found"}'
    assert recorded_sends == []
    with SessionLocal() as session:
        assert session.get(Appointment, foreign_id).technician_state is None


def test_technician_quick_action_rejects_non_technician_role(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _open_window_appointment(technician, "+56900000461")
    _login(client, "oper", "oper-pass")

    assert client.post(f"/panel/api/technician/appointments/{appointment_id}/en_route").status_code == 403


def test_technician_quick_action_requires_authenticated_session(client):
    response = client.post("/panel/api/technician/appointments/1/en_route")
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_technician_quick_action_cooldown_refuses_one_second_inside(client, make_user, recorded_sends):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _open_window_appointment(technician, "+56900000471")
    _prior_send_event(appointment_id, "appointment.en_route", 299)
    _login(client)

    response = client.post(f"/panel/api/technician/appointments/{appointment_id}/en_route")

    assert response.status_code == 429
    assert recorded_sends == []


def test_technician_quick_action_cooldown_allows_a_send_at_the_edge(client, make_user, mock_meta_send):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _open_window_appointment(technician, "+56900000472")
    _prior_send_event(appointment_id, "appointment.en_route", 300)
    _login(client)

    response = client.post(f"/panel/api/technician/appointments/{appointment_id}/en_route")

    assert response.status_code == 200
    assert _meta_template_body(mock_meta_send)["template"]["name"] == "en_route"


def test_technician_quick_action_cooldown_is_per_action(client, make_user, recorded_sends):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _open_window_appointment(technician, "+56900000473")
    _login(client)

    assert client.post(f"/panel/api/technician/appointments/{appointment_id}/en_route").status_code == 200
    assert client.post(f"/panel/api/technician/appointments/{appointment_id}/arrived").status_code == 200

    assert [template for _, _, template in recorded_sends] == ["en_route", "arrived"]


def test_technician_quick_action_cooldown_is_per_appointment(client, make_user, recorded_sends):
    first_tech = make_user("tech", "tech-pass", role="tecnico")
    second_tech = make_user("tech2", "tech2-pass", role="tecnico")
    first = _open_window_appointment(first_tech, "+56900000474")
    second = _open_window_appointment(second_tech, "+56900000475")
    _login(client)

    assert client.post(f"/panel/api/technician/appointments/{first}/en_route").status_code == 200
    _login(client, "tech2", "tech2-pass")
    assert client.post(f"/panel/api/technician/appointments/{second}/en_route").status_code == 200

    assert len(recorded_sends) == 2


def test_technician_quick_action_cooldown_reads_the_audit_log_not_the_state_column(client, make_user, recorded_sends):
    """S7: the cooldown comes from the last matching audit_log event."""
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _open_window_appointment(technician, "+56900000476")
    with SessionLocal() as session:
        session.query(Appointment).filter_by(id=appointment_id).update(
            {"technician_state": TechnicianVisitState.EN_ROUTE, "technician_state_at": datetime.now(timezone.utc)}
        )
        session.commit()
    _login(client)

    response = client.post(f"/panel/api/technician/appointments/{appointment_id}/en_route")

    assert response.status_code == 200, response.text  # recent state, no audit event -> no cooldown
    assert len(recorded_sends) == 1


def test_technician_quick_action_error_bodies_carry_no_customer_data(client, make_user, recorded_sends):
    technician = make_user("tech", "tech-pass", role="tecnico")
    far = _open_window_appointment(technician, "+56900000478", minutes_ahead=240)
    live = _open_window_appointment(technician, "+56900000479", local_time=time(14))
    _login(client)
    assert client.post(f"/panel/api/technician/appointments/{live}/en_route").status_code == 200

    responses = [
        client.post("/panel/api/technician/appointments/999999/arrived"),
        client.post(f"/panel/api/technician/appointments/{far}/arrived"),
        client.post(f"/panel/api/technician/appointments/{live}/en_route"),
    ]

    assert [response.status_code for response in responses] == [404, 409, 429]
    for response in responses:
        for token in ("+56900000478", "+56900000479", "phone", "email", "consent", "history", "conversation"):
            assert token not in response.text, (response.status_code, token, response.text)


def test_technician_quick_action_unreachable_customer_fails_without_writing(client, make_user, recorded_sends):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _open_window_appointment(technician, "")
    _login(client)
    before = _snapshot(appointment_id, "appointment.arrived")

    response = client.post(f"/panel/api/technician/appointments/{appointment_id}/arrived")

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "notification_failed"
    assert "phone" not in response.text
    assert recorded_sends == []
    assert _snapshot(appointment_id, "appointment.arrived") == before


def test_technician_quick_action_genuine_resend_sends_and_audits_twice(client, make_user, recorded_sends):
    technician = make_user("tech", "tech-pass", role="tecnico")
    appointment_id = _open_window_appointment(technician, "+56900000481")
    first = datetime.now(timezone.utc)
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        visit_actions.notify_customer(session, appointment, state=TechnicianVisitState.EN_ROUTE, actor="tech", now=first)
        session.commit()
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        visit_actions.notify_customer(session, appointment, state=TechnicianVisitState.EN_ROUTE, actor="tech", now=first + timedelta(seconds=301))
        session.commit()

    assert [template for _, _, template in recorded_sends] == ["en_route", "en_route"]
    with SessionLocal() as session:
        assert session.query(AuditLog).filter_by(action="appointment.en_route", entity_id=str(appointment_id)).count() == 2


def test_readonly_office_reads_never_mutate_the_field_state(client, make_user):
    """S9 non-regression: the office reads are reads. Once signed in, a marked
    state, its audit trail and the history stay identical after a successful
    detail read, a successful agenda read, an unknown id and a malformed range.

    The snapshot is taken after the login: signing in is a mutation by design
    (`app/panel/api/routes/auth.py` audits it), so it cannot be part of a
    read-only invariant."""
    technician = make_user("tech", "tech-pass", role="tecnico")
    make_user("oper", "oper-pass", role="operador")
    appointment_id = _appointment(technician, "+56900000075", date(2026, 2, 10), "state")
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        appointment.technician_state = TechnicianVisitState.EN_ROUTE
        appointment.technician_state_at = datetime(2026, 2, 10, 13, 45, tzinfo=timezone.utc)
        session.commit()

    assert client.post("/panel/api/login", json={"username": "oper", "password": "oper-pass"}).status_code == 200
    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        before = (appointment.technician_state, appointment.technician_state_at,
                  session.query(AuditLog).count(), session.query(AppointmentHistory).count())

    assert client.get(f"/panel/api/appointments/{appointment_id}").status_code == 200
    assert client.get("/panel/api/appointments?from=2026-02-10&to=2026-02-11&timezone=America/Santiago").status_code == 200
    assert client.get("/panel/api/appointments/999999").status_code == 404
    assert client.get("/panel/api/appointments?from=x&to=2026-02-11&timezone=UTC").status_code in (400, 422)

    with SessionLocal() as session:
        appointment = session.get(Appointment, appointment_id)
        assert (appointment.technician_state, appointment.technician_state_at,
                session.query(AuditLog).count(), session.query(AppointmentHistory).count()) == before
