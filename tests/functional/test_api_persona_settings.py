"""S12/S13 panel API — persona and emergency protocol: edit, versions, restore.

The editable prompt/protocol is an override in the settings KV. Version history
is the append-only audit trail every settings write already produces, so a
"version" is one audited state of the key and version ``0`` means "the bundled
default" (row absent).

Covers:
- GET /settings exposes both sections with the effective text and `customized`
- POST persists only after validation (a persona that breaks the contract is
  never stored), one audit entry per save
- GET /settings/versions/{scope} lists saved versions oldest-first
- GET /settings/versions/{scope}/diff?from=&to= returns a unified diff per field
- POST /settings/versions/{scope}/restore writes a version back (or deletes the
  row for version 0) and is itself audited
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db import SessionLocal  # noqa: E402
from app.models import AuditLog, Settings  # noqa: E402
from app.services import prompts, settings as settings_service  # noqa: E402

_ORCHESTRATOR = "personas/orchestrator.md"
_BRIEF = "personas/orchestrator_brief.md"
PERSONA = "/panel/api/settings/persona"
EMERGENCY = "/panel/api/settings/emergency"


def _login(client, username: str = "adm", password: str = "adm-pass") -> None:
    resp = client.post(
        "/panel/api/login",
        json={"username": username, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 200, f"api login must succeed: {resp.status_code} {resp.text}"


def _last_audit(action: str) -> AuditLog | None:
    with SessionLocal() as session:
        return session.scalar(
            select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.id.desc())
        )


def _persona_body(orchestrator: str = "Eres Max, edición uno.", brief: str = "Sé breve.") -> dict:
    return {"orchestrator": orchestrator, "orchestrator_brief": brief}


_PROTOCOL = {
    "safety_instructions": ["Corta el gas solo si es seguro.", "Ventila el lugar."],
    "contacts": ["Bomberos 132."],
    "notify_message": "Un técnico de Lumat fue notificado.",
}


@pytest.fixture
def admin(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    return client


# --- GET /settings -----------------------------------------------------------


def test_settings_get_exposes_the_bundled_persona_and_protocol(admin):
    payload = admin.get("/panel/api/settings").json()

    assert payload["persona"] == {
        "orchestrator": prompts.FALLBACKS[_ORCHESTRATOR],
        "orchestrator_brief": prompts.FALLBACKS[_BRIEF],
        "customized": False,
    }
    assert payload["emergency"] == {
        "safety_instructions": settings_service.DEFAULT_SAFETY_INSTRUCTIONS,
        "contacts": settings_service.DEFAULT_EMERGENCY_CONTACTS,
        "notify_message": settings_service.DEFAULT_EMERGENCY_NOTIFY_MESSAGE,
        "customized": False,
    }


# --- POST /settings/persona --------------------------------------------------


def test_persona_save_persists_one_row_and_one_audit_entry(admin):
    resp = admin.post(PERSONA, json=_persona_body(), follow_redirects=False)

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    with SessionLocal() as session:
        stored = session.get(Settings, settings_service.PERSONA_TEXTS_KEY)
        assert stored.value == {_ORCHESTRATOR: "Eres Max, edición uno.", _BRIEF: "Sé breve."}
    audit = _last_audit("settings.change")
    assert audit is not None and audit.actor == "adm"
    assert audit.entity_id == settings_service.PERSONA_TEXTS_KEY


def test_persona_save_is_visible_in_the_settings_payload(admin):
    admin.post(PERSONA, json=_persona_body(), follow_redirects=False)

    persona = admin.get("/panel/api/settings").json()["persona"]
    assert persona["orchestrator"] == "Eres Max, edición uno."
    assert persona["customized"] is True


def test_persona_that_breaks_the_contract_is_not_persisted(admin):
    resp = admin.post(
        PERSONA,
        json=_persona_body(orchestrator="Eres Max. Saluda a {{nombre}}."),
        follow_redirects=False,
    )

    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/json")
    with SessionLocal() as session:
        assert session.get(Settings, settings_service.PERSONA_TEXTS_KEY) is None
    assert _last_audit("settings.change") is None


@pytest.mark.parametrize(
    "text",
    [
        "Eres Max. Saluda a {{nombre del cliente}}.",
        "Eres Max. Saluda a {{nombre-del-cliente}}.",
        "Eres Max. Saluda a {{nombre.cliente}}.",
        "Eres Max. Saluda a {{}}.",
        "Eres Max. Saluda a {{ nombre",
    ],
)
def test_persona_with_a_malformed_mustache_is_not_persisted(admin, text):
    resp = admin.post(PERSONA, json=_persona_body(orchestrator=text), follow_redirects=False)

    assert resp.status_code == 400
    with SessionLocal() as session:
        assert session.get(Settings, settings_service.PERSONA_TEXTS_KEY) is None
    assert _last_audit("settings.change") is None


def test_persona_save_rejects_unknown_fields_instead_of_dropping_them(admin):
    resp = admin.post(
        PERSONA,
        json={**_persona_body(), _ORCHESTRATOR: "no debería guardarse"},
        follow_redirects=False,
    )

    assert resp.status_code == 422
    with SessionLocal() as session:
        assert session.get(Settings, settings_service.PERSONA_TEXTS_KEY) is None


def test_emergency_save_rejects_unknown_fields_instead_of_dropping_them(admin):
    resp = admin.post(
        EMERGENCY, json={**_PROTOCOL, "silence_everything": True}, follow_redirects=False
    )

    assert resp.status_code == 422
    with SessionLocal() as session:
        assert session.get(Settings, settings_service.EMERGENCY_PROTOCOL_KEY) is None


def test_persona_save_requires_both_texts(admin):
    resp = admin.post(
        PERSONA, json={"orchestrator": "Eres Max."}, follow_redirects=False
    )

    assert resp.status_code == 422


# --- versions ----------------------------------------------------------------


def test_versions_list_one_entry_per_saved_state(admin):
    admin.post(PERSONA, json=_persona_body(), follow_redirects=False)
    admin.post(PERSONA, json=_persona_body("Eres Max, edición dos."), follow_redirects=False)

    versions = admin.get("/panel/api/settings/versions/persona").json()["versions"]

    assert [entry["version"] for entry in versions] == [1, 2]
    assert versions[0]["content"]["orchestrator"] == "Eres Max, edición uno."
    assert versions[1]["content"]["orchestrator"] == "Eres Max, edición dos."
    assert versions[0]["actor"] == "adm"


def test_versions_list_is_empty_before_the_first_save(admin):
    assert admin.get("/panel/api/settings/versions/persona").json() == {"versions": []}


def test_versions_diff_between_two_states(admin):
    admin.post(PERSONA, json=_persona_body(), follow_redirects=False)
    admin.post(PERSONA, json=_persona_body("Eres Max, edición dos."), follow_redirects=False)

    payload = admin.get("/panel/api/settings/versions/persona/diff?from=1&to=2").json()

    diff = payload["diff"]["orchestrator"]
    assert "-Eres Max, edición uno." in diff
    assert "+Eres Max, edición dos." in diff


def test_versions_diff_against_the_bundled_default(admin):
    admin.post(PERSONA, json=_persona_body(), follow_redirects=False)

    payload = admin.get("/panel/api/settings/versions/persona/diff?from=0&to=1").json()

    assert "+Eres Max, edición uno." in payload["diff"]["orchestrator"]


def test_versions_diff_rejects_an_unknown_version(admin):
    admin.post(PERSONA, json=_persona_body(), follow_redirects=False)

    resp = admin.get("/panel/api/settings/versions/persona/diff?from=1&to=99")

    assert resp.status_code == 404


def test_restore_writes_a_previous_version_back(admin):
    admin.post(PERSONA, json=_persona_body(), follow_redirects=False)
    admin.post(PERSONA, json=_persona_body("Eres Max, edición dos."), follow_redirects=False)

    resp = admin.post(
        "/panel/api/settings/versions/persona/restore",
        json={"version": 1},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    persona = admin.get("/panel/api/settings").json()["persona"]
    assert persona["orchestrator"] == "Eres Max, edición uno."
    # restoring is a new audited state, not a rewrite of history
    versions = admin.get("/panel/api/settings/versions/persona").json()["versions"]
    assert [entry["version"] for entry in versions] == [1, 2, 3]
    assert versions[2]["content"]["orchestrator"] == "Eres Max, edición uno."


def test_restore_version_zero_returns_to_the_bundled_default(admin):
    admin.post(PERSONA, json=_persona_body(), follow_redirects=False)

    resp = admin.post(
        "/panel/api/settings/versions/persona/restore",
        json={"version": 0},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    persona = admin.get("/panel/api/settings").json()["persona"]
    assert persona["customized"] is False
    assert persona["orchestrator"] == prompts.FALLBACKS[_ORCHESTRATOR]
    with SessionLocal() as session:
        assert session.get(Settings, settings_service.PERSONA_TEXTS_KEY) is None
    assert _last_audit("settings.reset") is not None


def test_restore_rejects_an_unknown_version(admin):
    resp = admin.post(
        "/panel/api/settings/versions/persona/restore",
        json={"version": 7},
        follow_redirects=False,
    )

    assert resp.status_code == 404


def test_versions_reject_an_unknown_scope(admin):
    assert admin.get("/panel/api/settings/versions/inventado").status_code == 404


# --- POST /settings/emergency ------------------------------------------------


def test_emergency_save_persists_and_is_read_by_the_service(admin):
    resp = admin.post(EMERGENCY, json=_PROTOCOL, follow_redirects=False)

    assert resp.status_code == 200
    with SessionLocal() as session:
        assert session.get(Settings, settings_service.EMERGENCY_PROTOCOL_KEY).value == _PROTOCOL
        assert settings_service.get_emergency_protocol(session) == _PROTOCOL
    audit = _last_audit("settings.change")
    assert audit is not None and audit.entity_id == settings_service.EMERGENCY_PROTOCOL_KEY


def test_emergency_save_rejects_an_empty_protocol_without_persisting(admin):
    resp = admin.post(
        EMERGENCY,
        json={**_PROTOCOL, "safety_instructions": []},
        follow_redirects=False,
    )

    assert resp.status_code == 400
    with SessionLocal() as session:
        assert session.get(Settings, settings_service.EMERGENCY_PROTOCOL_KEY) is None


def test_emergency_versions_and_restore_share_the_same_surface(admin):
    admin.post(EMERGENCY, json=_PROTOCOL, follow_redirects=False)
    changed = {**_PROTOCOL, "notify_message": "Un asesor te contactará."}
    admin.post(EMERGENCY, json=changed, follow_redirects=False)

    versions = admin.get("/panel/api/settings/versions/emergency").json()["versions"]
    assert [entry["version"] for entry in versions] == [1, 2]

    diff = admin.get("/panel/api/settings/versions/emergency/diff?from=1&to=2").json()["diff"]
    assert "+Un asesor te contactará." in diff["notify_message"]

    admin.post(
        "/panel/api/settings/versions/emergency/restore",
        json={"version": 1},
        follow_redirects=False,
    )
    with SessionLocal() as session:
        assert settings_service.get_emergency_protocol(session)["notify_message"] == (
            _PROTOCOL["notify_message"]
        )


def test_emergency_restore_zero_returns_to_the_shipped_protocol(admin):
    admin.post(EMERGENCY, json=_PROTOCOL, follow_redirects=False)

    admin.post(
        "/panel/api/settings/versions/emergency/restore",
        json={"version": 0},
        follow_redirects=False,
    )

    with SessionLocal() as session:
        assert settings_service.get_emergency_protocol(session) == {
            "safety_instructions": settings_service.DEFAULT_SAFETY_INSTRUCTIONS,
            "contacts": settings_service.DEFAULT_EMERGENCY_CONTACTS,
            "notify_message": settings_service.DEFAULT_EMERGENCY_NOTIFY_MESSAGE,
        }
    assert admin.get("/panel/api/settings").json()["emergency"]["customized"] is False
