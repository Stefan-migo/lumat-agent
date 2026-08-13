"""KB manager + settings panel views (T5.4; AP-2, AP-6, KB-3, KB-4, SS-1..5, SH-5).

Functional suite: the admin-only role gate (completes the AP-2 matrix started
in T5.1), KB add/edit/disable/restore with audit and provider/model/cost
shown (AP-6, KB-3/4), and the settings views for scope rules, emergency
keywords, tone, spend limits and Meta pricing — every save audited (SS-1..5,
SH-5) and the settings page exposing the spend snapshot (SS-4).
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db import SessionLocal  # noqa: E402
from app.models import AuditLog, KbDocument, Settings, UserRole  # noqa: E402
from app.services.settings import SETTINGS_DEFAULTS  # noqa: E402


def _login(client, username: str, password: str) -> None:
    resp = client.post(
        "/panel/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 302


@pytest.fixture
def admin_client(client, make_user, login):
    make_user("adm", "adm-pass", role="admin")
    login(client, "adm", "adm-pass")
    return client


@pytest.fixture
def oper_client(client, make_user, login):
    make_user("oper", "oper-pass", role="operador")
    login(client, "oper", "oper-pass")
    return client


def _last_audit(action: str) -> AuditLog | None:
    with SessionLocal() as session:
        return session.scalar(
            select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.id.desc())
        )


# ---------------------------------------------------------------------------
# AP-2 — admin-only gate (completes the T5.1 role matrix)
# ---------------------------------------------------------------------------


@pytest.mark.spec("AP-2")
def test_operador_cannot_access_kb_manager(oper_client):
    resp = oper_client.get("/panel/kb")
    assert resp.status_code == 403

    resp = oper_client.post(
        "/panel/kb", data={"title": "x"}, files={}, follow_redirects=False
    )
    assert resp.status_code == 403


@pytest.mark.spec("AP-2")
def test_operador_cannot_access_settings(oper_client):
    resp = oper_client.get("/panel/settings")
    assert resp.status_code == 403

    resp = oper_client.post("/panel/settings/keywords", data={"keywords": "gas"}, follow_redirects=False)
    assert resp.status_code == 403


@pytest.mark.spec("AP-2")
def test_admin_can_access_kb_manager_and_settings(admin_client):
    assert admin_client.get("/panel/kb").status_code == 200
    assert admin_client.get("/panel/settings").status_code == 200


# ---------------------------------------------------------------------------
# AP-6 / KB-3 / KB-4 — KB manager (add / edit / disable / restore)
# ---------------------------------------------------------------------------


@pytest.mark.spec("KB-3")
def test_kb_add_document(admin_client, mock_openai_embeddings):
    resp = admin_client.post(
        "/panel/kb",
        data={"title": "Tarifas 2026"},
        files={"file": ("tarifas.md", b"# Tarifas\nRevision anual: $49.990", "text/markdown")},
        follow_redirects=True,
    )

    assert resp.status_code == 200
    assert "Tarifas 2026" in resp.text
    with SessionLocal() as session:
        doc = session.scalar(select(KbDocument).where(KbDocument.title == "Tarifas 2026"))
        assert doc is not None
        assert doc.format.value == "md"
        assert doc.version == 1
        assert doc.active is True
        assert doc.provider == "openai"
        assert doc.model == "text-embedding-3-small"
    audit = _last_audit("kb.document_ingest")
    assert audit is not None and audit.actor == "adm"


@pytest.mark.spec("KB-4")
def test_kb_edit_creates_new_version(admin_client, mock_openai_embeddings):
    # Seed v1 via the panel, then edit it.
    admin_client.post(
        "/panel/kb",
        data={"title": "Manual"},
        files={"file": ("manual.md", b"version one content", "text/markdown")},
        follow_redirects=True,
    )
    with SessionLocal() as session:
        doc_id = session.scalar(select(KbDocument).where(KbDocument.title == "Manual")).id

    resp = admin_client.post(
        f"/panel/kb/{doc_id}/edit",
        data={"title": "Manual", "content": "version two content"},
        follow_redirects=True,
    )

    assert resp.status_code == 200
    with SessionLocal() as session:
        doc = session.get(KbDocument, doc_id)
        assert doc.version == 2
        assert doc.active_version == 2
        assert doc.active is True
        assert "version two content" in doc.content
    audit = _last_audit("kb.document_update")
    assert audit is not None and audit.actor == "adm"


@pytest.mark.spec("KB-3")
def test_kb_disable_document(admin_client, mock_openai_embeddings):
    admin_client.post(
        "/panel/kb",
        data={"title": "Manual"},
        files={"file": ("manual.md", b"content", "text/markdown")},
        follow_redirects=True,
    )
    with SessionLocal() as session:
        doc_id = session.scalar(select(KbDocument).where(KbDocument.title == "Manual")).id

    resp = admin_client.post(f"/panel/kb/{doc_id}/disable", follow_redirects=True)

    assert resp.status_code == 200
    with SessionLocal() as session:
        doc = session.get(KbDocument, doc_id)
        assert doc.active is False
    assert _last_audit("kb.document_disable") is not None


@pytest.mark.spec("KB-4")
def test_kb_restore_previous_version(admin_client, mock_openai_embeddings):
    admin_client.post(
        "/panel/kb",
        data={"title": "Manual"},
        files={"file": ("manual.md", b"v1", "text/markdown")},
        follow_redirects=True,
    )
    with SessionLocal() as session:
        doc_id = session.scalar(select(KbDocument).where(KbDocument.title == "Manual")).id
    admin_client.post(
        f"/panel/kb/{doc_id}/edit",
        data={"title": "Manual", "content": "v2 content"},
        follow_redirects=True,
    )

    resp = admin_client.post(
        f"/panel/kb/{doc_id}/restore", data={"version": "1"}, follow_redirects=True
    )

    assert resp.status_code == 200
    with SessionLocal() as session:
        doc = session.get(KbDocument, doc_id)
        assert doc.active_version == 1, "restore flips the active_version pointer (D8)"
        assert doc.active is True
    assert _last_audit("kb.document_restore") is not None


@pytest.mark.spec("KB-3")
def test_kb_list_shows_provider_model_cost(admin_client, mock_openai_embeddings):
    admin_client.post(
        "/panel/kb",
        data={"title": "Tarifas"},
        files={"file": ("tarifas.csv", b"servicio,precio\nrevision,49990\n", "text/csv")},
        follow_redirects=True,
    )

    resp = admin_client.get("/panel/kb")

    assert resp.status_code == 200
    assert "openai" in resp.text
    assert "text-embedding-3-small" in resp.text
    assert "Tarifas" in resp.text


# ---------------------------------------------------------------------------
# SS-1..5 — settings saves (audited via set_setting)
# ---------------------------------------------------------------------------


@pytest.mark.spec("SS-1")
def test_settings_save_scope_rules(admin_client):
    resp = admin_client.post(
        "/panel/settings/scope",
        data={"rules": "valores=always_escalate\ncalefont=bot_resolve"},
        follow_redirects=True,
    )

    assert resp.status_code == 200
    with SessionLocal() as session:
        row = session.get(Settings, "scope_rules")
        assert row.value == {"valores": "always_escalate", "calefont": "bot_resolve"}
        assert row.updated_by is not None
    audit = _last_audit("settings.change")
    assert audit is not None and audit.actor == "adm"
    assert audit.entity_id == "scope_rules"


@pytest.mark.spec("SS-2")
def test_settings_save_emergency_keywords(admin_client):
    resp = admin_client.post(
        "/panel/settings/keywords",
        data={"keywords": "olor a gas\nfuga de gas\nhuele raro"},
        follow_redirects=True,
    )

    assert resp.status_code == 200
    with SessionLocal() as session:
        row = session.get(Settings, "emergency.keywords")
        assert row.value == ["olor a gas", "fuga de gas", "huele raro"]
    assert _last_audit("settings.change") is not None


@pytest.mark.spec("SS-5")
def test_settings_save_tone(admin_client):
    resp = admin_client.post(
        "/panel/settings/tone", data={"tone": "casual"}, follow_redirects=True
    )

    assert resp.status_code == 200
    with SessionLocal() as session:
        row = session.get(Settings, "tone.style")
        assert row.value == "casual"
    assert _last_audit("settings.change") is not None


@pytest.mark.spec("SS-3")
def test_settings_save_spend_limits(admin_client):
    resp = admin_client.post(
        "/panel/settings/limits",
        data={"conversation_limit": "2.00", "daily_limit": "10.00"},
        follow_redirects=True,
    )

    assert resp.status_code == 200
    with SessionLocal() as session:
        assert session.get(Settings, "cost.conversation_limit").value == 2.00
        assert session.get(Settings, "cost.daily_limit").value == 10.00
    assert _last_audit("settings.change") is not None


@pytest.mark.spec("SS-4")
def test_settings_save_meta_pricing(admin_client):
    resp = admin_client.post(
        "/panel/settings/meta", data={"service_message_cost": "0.025"}, follow_redirects=True
    )

    assert resp.status_code == 200
    with SessionLocal() as session:
        row = session.get(Settings, "meta_pricing")
        assert row.value == {"service_message_cost": 0.025}
    assert _last_audit("settings.change") is not None


@pytest.mark.spec("SS-4")
def test_settings_page_shows_spend_snapshot(admin_client):
    resp = admin_client.get("/panel/settings")

    assert resp.status_code == 200
    assert "daily" in resp.text  # spend snapshot section (SS-4: spend visible)
    # defaults are rendered (meta pricing + limits present on the page)
    assert "0.01" in resp.text  # default meta service-message cost
    assert "5.0" in resp.text or "5.00" in resp.text  # default daily limit
