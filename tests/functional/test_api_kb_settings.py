"""Panel JSON API KB + settings (B4/T4.1+T4.2; PDW-API-1/2/3/4, D1, D4).

Admin-only JSON endpoints over `app/services/kb.py` + `app/services/settings.py`
+ `app/services/costs.py` (thin wrappers, no new business logic; audits are the
existing service calls, SH-5):

KB (endpoints 13-17):
- GET  /panel/api/kb               -> {"docs": [{provider, model, cost_meta}]}
- GET  /panel/api/kb/{id}           -> document detail including content
- GET  /panel/api/kb/search         -> retrieval probe
- POST /panel/api/kb               -> multipart title + file (pdf/md/txt/csv)
                                     ingest + audit (PDW-API-1)
- POST /panel/api/kb/{id}/edit     -> {"title","content"} new version re-embed
- POST /panel/api/kb/{id}/disable  -> KB-3 disable, audited
- POST /panel/api/kb/{id}/enable   -> re-enable without changing version or visibility
- POST /panel/api/kb/{id}/restore  -> {"version":n} pointer flip, audited (D8)
- POST /panel/api/kb/{id}/visibility -> {"visibility":...} reclassification, audited

Settings (endpoints 18-19):
- GET  /panel/api/settings                         -> all sections + snapshot
- POST /panel/api/settings/{section}               -> KV upsert + audit
                                     (section: scope|keywords|tone|limits|meta)

Role enforcement server-side (PDW-API-4): admin 200, operador -> 403 JSON
{"detail":"admin role required"}; unauthenticated -> 401 JSON {"detail":
"unauthorized"} with no redirect (PDW-AUTH-1, D4). No CORS (D1). Errors are
always JSON {"detail": ...} (PDW-API-3). KB ingest uses the `fake_embedder`
fixture so no model is ever downloaded.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db import SessionLocal  # noqa: E402
from app.models import AuditLog, KbDocument, Project, Settings  # noqa: E402
from app.services import kb as kb_service  # noqa: E402


def _login(client, username: str = "adm", password: str = "adm-pass") -> None:
    resp = client.post(
        "/panel/api/login",
        json={"username": username, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 200, f"api login must succeed: {resp.status_code} {resp.text}"


def _seed_doc(*, title: str = "Tarifas 2026", content: bytes = b"# Tarifas\nRevision anual: $49.990",
              ext: str = ".md") -> int:
    """Seed a KB document through the service path (v1, embedded)."""
    from app.models import DocumentFormat

    fmt = {".pdf": DocumentFormat.PDF, ".md": DocumentFormat.MD, ".csv": DocumentFormat.CSV}[ext]
    with SessionLocal() as session:
        doc = kb_service.ingest_document(
            session, title, fmt, content, source_meta={"seed": True}, actor="seed"
        )
        session.commit()
        return doc.id


def _seed_version2(*, doc_id: int, content: str = "version two content") -> None:
    """Seed a second version so restore has a previous pointer to flip to."""
    with SessionLocal() as session:
        kb_service.update_document(session, doc_id, content, title="Tarifas 2026", actor="seed")
        session.commit()


def _last_audit(action: str) -> AuditLog | None:
    with SessionLocal() as session:
        return session.scalar(
            select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.id.desc())
        )


# ---------------------------------------------------------------------------
# PDW-AUTH-1 — unauthenticated: every KB/settings route answers 401 JSON
# ---------------------------------------------------------------------------


def test_kb_endpoints_require_login_401_json(client):
    """No session -> every KB endpoint answers 401 JSON, never a 302 (D1 P4)."""
    kb_calls = [
        ("get", "/panel/api/kb"),
        ("get", "/panel/api/kb/1"),
        ("get", "/panel/api/kb/search?q=tarifas"),
        ("post", "/panel/api/kb"),
        ("post", "/panel/api/kb/1/edit"),
        ("post", "/panel/api/kb/1/disable"),
        ("post", "/panel/api/kb/1/enable"),
        ("post", "/panel/api/kb/1/restore"),
        ("post", "/panel/api/kb/1/visibility"),
    ]
    for method, path in kb_calls:
        resp = getattr(client, method)(path, follow_redirects=False)
        assert resp.status_code == 401, f"{method.upper()} {path} must be 401"
        assert "location" not in resp.headers, f"{path} must not redirect (PDW-AUTH-1)"
        assert resp.headers["content-type"].startswith("application/json"), (
            f"{path} error must be JSON (PDW-API-3)"
        )
        assert resp.json() == {"detail": "unauthorized"}
        assert "access-control-allow-origin" not in resp.headers, "no CORS (D1)"


def test_settings_endpoints_require_login_401_json(client):
    settings_calls = [
        ("get", "/panel/api/settings"),
        ("post", "/panel/api/settings/scope", {"rules": {}}),
        ("post", "/panel/api/settings/keywords", {"keywords": ["gas"]}),
        ("post", "/panel/api/settings/tone", {"tone": "casual"}),
        ("post", "/panel/api/settings/limits", {"conversation_limit": 2.0, "daily_limit": 5.0}),
        ("post", "/panel/api/settings/meta", {"service_message_cost": 0.01}),
        ("post", "/panel/api/settings/unknown", {}),
    ]
    for method, path, *body in settings_calls:
        kwargs = {"json": body[0], "follow_redirects": False} if body else {"follow_redirects": False}
        resp = getattr(client, method)(path, **kwargs)
        assert resp.status_code == 401, f"{method.upper()} {path} must be 401"
        assert "location" not in resp.headers, f"{path} must not redirect (PDW-AUTH-1)"
        assert resp.headers["content-type"].startswith("application/json"), (
            f"{path} error must be JSON (PDW-API-3)"
        )
        assert resp.json() == {"detail": "unauthorized"}
        assert "access-control-allow-origin" not in resp.headers, "no CORS (D1)"


# ---------------------------------------------------------------------------
# PDW-API-4 — operador is denied 403 JSON on every admin endpoint
# ---------------------------------------------------------------------------


def test_kb_endpoints_denied_403_for_operador_json(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    _login(client, "oper", "oper-pass")
    kb_calls = [
        ("get", "/panel/api/kb"),
        ("get", "/panel/api/kb/1"),
        ("get", "/panel/api/kb/search?q=tarifas"),
        ("post", "/panel/api/kb"),
        ("post", "/panel/api/kb/1/edit"),
        ("post", "/panel/api/kb/1/disable"),
        ("post", "/panel/api/kb/1/enable"),
        ("post", "/panel/api/kb/1/restore"),
        ("post", "/panel/api/kb/1/visibility"),
    ]
    for method, path in kb_calls:
        resp = getattr(client, method)(path, follow_redirects=False)
        assert resp.status_code == 403, f"{method.upper()} {path} must be 403 for operador"
        assert resp.headers["content-type"].startswith("application/json")
        assert resp.json() == {"detail": "admin role required"}


def test_settings_endpoints_denied_403_for_operador_json(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    _login(client, "oper", "oper-pass")
    settings_calls = [
        ("get", "/panel/api/settings", None),
        ("post", "/panel/api/settings/scope", {"rules": {"valores": "always_escalate"}}),
        ("post", "/panel/api/settings/tone", {"tone": "casual"}),
    ]
    for method, path, body in settings_calls:
        kwargs = {"follow_redirects": False}
        if body is not None:
            kwargs["json"] = body
        resp = getattr(client, method)(path, **kwargs)
        assert resp.status_code == 403, f"{method.upper()} {path} must be 403 for operador"
        assert resp.headers["content-type"].startswith("application/json")
        assert resp.json() == {"detail": "admin role required"}


# ---------------------------------------------------------------------------
# PDW-API / KB — GET /kb list + all mutations
# ---------------------------------------------------------------------------


def test_kb_list_returns_docs_with_provider_model_cost(client, make_user, fake_embedder):
    _seed_doc(title="Tarifas", content=b"servicio,precio\nrevision,49990\n", ext=".csv")
    _seed_doc(title="Manual", content=b"# Manual\nStep one\n" * 20)
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.get("/panel/api/kb", follow_redirects=False)

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"docs"}
    docs = body["docs"]
    assert len(docs) == 2
    # newest first (id desc)
    assert docs[0]["title"] == "Manual"
    assert docs[1]["title"] == "Tarifas"
    # provider/model/cost exposed (AP-6, design #13 shape)
    assert docs[0]["provider"] == kb_service.PROVIDER
    assert docs[0]["model"] == kb_service.EMBED_MODEL
    assert docs[0]["cost_meta"] == 0.0
    # active flag present (KB-3 state) + ISO-8601 datetime
    assert docs[0]["active"] is True
    from datetime import datetime, timezone

    datetime.fromisoformat(docs[0]["created_at"])
    assert all("id" in d and "title" in d and "version" in d for d in docs)
    assert all("content" not in d for d in docs)


def test_kb_detail_returns_content(client, make_user, fake_embedder):
    doc_id = _seed_doc(content=b"stored document content")
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.get(f"/panel/api/kb/{doc_id}", follow_redirects=False)

    assert resp.status_code == 200
    assert resp.json()["content"] == "stored document content"


def test_kb_detail_missing_doc_404_json(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.get("/panel/api/kb/999999", follow_redirects=False)

    assert resp.status_code == 404
    assert resp.json() == {"detail": "kb document not found"}


def test_kb_search_returns_ranked_title_and_similarity(client, make_user, fake_embedder):
    doc_id = _seed_doc(title="Tarifas 2026", content=b"revision anual precio gas")
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.get("/panel/api/kb/search?q=revision anual precio gas", follow_redirects=False)

    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["document_id"] == doc_id
    assert result["title"] == "Tarifas 2026"
    assert result["similarity"] > 0


def test_kb_search_filters_threshold_and_disabled_documents(client, make_user, fake_embedder):
    doc_id = _seed_doc(title="Enabled", content=b"common retrieval phrase")
    disabled_id = _seed_doc(title="Disabled", content=b"common retrieval phrase")
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    client.post(f"/panel/api/kb/{disabled_id}/disable", follow_redirects=False)

    hit = client.get("/panel/api/kb/search?q=common retrieval phrase&min_sim=0", follow_redirects=False)
    miss = client.get("/panel/api/kb/search?q=unrelated&min_sim=1", follow_redirects=False)

    assert [item["document_id"] for item in hit.json()["results"]] == [doc_id]
    assert miss.json() == {"results": []}


def test_kb_search_honors_top_k_and_min_sim(client, make_user, fake_embedder):
    _seed_doc(title="One", content=b"shared phrase one")
    _seed_doc(title="Two", content=b"shared phrase two")
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    limited = client.get("/panel/api/kb/search?q=shared phrase&top_k=1&min_sim=0")
    low = client.get("/panel/api/kb/search?q=shared phrase&min_sim=0")
    high = client.get("/panel/api/kb/search?q=shared phrase&min_sim=1")

    assert len(limited.json()["results"]) == 1
    assert len(low.json()["results"]) >= len(high.json()["results"])


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("top_k", "0"),
        ("top_k", "-1"),
        ("top_k", "51"),
        ("min_sim", "-2"),
        ("min_sim", "2"),
    ],
)
def test_kb_search_rejects_out_of_range_probe_parameters(
    client, make_user, fake_embedder, parameter, value
):
    _seed_doc()
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.get(f"/panel/api/kb/search?q=tarifas&{parameter}={value}")

    assert resp.status_code == 422


def test_kb_search_accepts_inclusive_top_k_upper_bound(client, make_user, fake_embedder):
    _seed_doc()
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.get("/panel/api/kb/search?q=tarifas&top_k=50")

    assert resp.status_code == 200


def test_kb_search_blank_query_400_json(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.get("/panel/api/kb/search?q=%20%20", follow_redirects=False)

    assert resp.status_code == 400
    assert "detail" in resp.json()


def test_kb_upload_ingests_and_audits(client, make_user, fake_embedder):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        "/panel/api/kb",
        data={"title": "Tarifas 2026"},
        files={"file": ("tarifas.md", b"# Tarifas\nRevision anual: $49.990", "text/markdown")},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"ok", "doc"}
    assert body["ok"] is True
    assert body["doc"]["title"] == "Tarifas 2026"
    assert body["doc"]["format"] == "md"
    assert body["doc"]["version"] == 1
    assert body["doc"]["active"] is True
    doc_id = body["doc"]["id"]
    # persisted (PDW-API-1: new document returned)
    with SessionLocal() as session:
        doc = session.get(KbDocument, doc_id)
        assert doc is not None
        assert doc.format.value == "md"
        assert doc.provider == "local"
        assert doc.model == kb_service.EMBED_MODEL
    # audited with the acting admin (SH-5, PDW-API-1)
    audit = _last_audit("kb.document_ingest")
    assert audit is not None
    assert audit.actor == "adm"
    assert audit.after == {
        "title": "Tarifas 2026",
        "format": "md",
        "version": 1,
        "visibility": "internal",
    }


def _seed_project(owner_id: int, slug: str) -> int:
    from app.services.kb import EMBED_DIMS

    with SessionLocal() as session:
        project = Project(
            owner_id=owner_id,
            slug=slug,
            name=slug.title(),
            purpose=f"Purpose for {slug}",
            purpose_embedding=[0.0] * EMBED_DIMS,
        )
        session.add(project)
        session.flush()
        project_id = project.id
        session.commit()
        return project_id


def test_kb_upload_without_project_id_is_global(client, make_user, fake_embedder):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        "/panel/api/kb",
        data={"title": "Global guide"},
        files={"file": ("global.md", b"global content", "text/markdown")},
    )

    assert resp.status_code == 200
    assert resp.json()["doc"]["project_id"] is None


def test_kb_upload_binds_to_owned_project(client, make_user, fake_embedder):
    owner_id = make_user("adm", "adm-pass", role="admin")
    project_id = _seed_project(owner_id, "owned")
    _login(client)

    resp = client.post(
        "/panel/api/kb",
        data={"title": "Project guide", "project_id": str(project_id)},
        files={"file": ("project.md", b"project content", "text/markdown")},
    )

    assert resp.status_code == 200
    assert resp.json()["doc"]["project_id"] == project_id


@pytest.mark.parametrize("foreign", [False, True], ids=["unknown", "another-owner"])
def test_kb_upload_rejects_unowned_project(client, make_user, fake_embedder, foreign):
    make_user("adm", "adm-pass", role="admin")
    if foreign:
        other_owner_id = make_user("other", "other-pass", role="admin")
        project_id = _seed_project(other_owner_id, "foreign")
    else:
        project_id = 999999
    _login(client)

    resp = client.post(
        "/panel/api/kb",
        data={"title": "Rejected guide", "project_id": str(project_id)},
        files={"file": ("rejected.md", b"content", "text/markdown")},
    )

    assert resp.status_code == 400
    assert "project" in resp.json()["detail"].lower()
    with SessionLocal() as session:
        assert session.scalar(select(KbDocument).where(KbDocument.title == "Rejected guide")) is None


def test_kb_upload_explicit_customer_visibility(client, make_user, fake_embedder):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        "/panel/api/kb",
        data={"title": "Customer guide", "visibility": "customer"},
        files={"file": ("guide.md", b"customer content", "text/markdown")},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    assert resp.json()["doc"]["visibility"] == "customer"
    with SessionLocal() as session:
        assert session.get(KbDocument, resp.json()["doc"]["id"]).visibility.value == "customer"


def test_kb_upload_without_visibility_defaults_internal(client, make_user, fake_embedder):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        "/panel/api/kb",
        data={"title": "Internal guide"},
        files={"file": ("guide.md", b"internal content", "text/markdown")},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    assert resp.json()["doc"]["visibility"] == "internal"
    audit = _last_audit("kb.document_ingest")
    assert audit is not None and audit.after["visibility"] == "internal"


def test_kb_upload_invalid_visibility_400_without_document(client, make_user, fake_embedder):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        "/panel/api/kb",
        data={"title": "Invalid", "visibility": "secret"},
        files={"file": ("invalid.md", b"content", "text/markdown")},
        follow_redirects=False,
    )

    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/json")
    assert "visibility" in resp.json()["detail"]
    with SessionLocal() as session:
        assert session.scalar(select(KbDocument).where(KbDocument.title == "Invalid")) is None


def test_kb_set_visibility_audits_without_new_version(client, make_user, fake_embedder):
    doc_id = _seed_doc()
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        f"/panel/api/kb/{doc_id}/visibility",
        json={"visibility": "customer"},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    assert resp.json()["doc"]["visibility"] == "customer"
    assert resp.json()["doc"]["version"] == 1
    with SessionLocal() as session:
        doc = session.get(KbDocument, doc_id)
        assert doc.visibility.value == "customer"
        assert doc.version == 1
    audit = _last_audit("kb.document_visibility")
    assert audit is not None and audit.actor == "adm"
    assert audit.before == {"visibility": "internal"}
    assert audit.after == {"visibility": "customer"}


def test_kb_set_visibility_missing_doc_404_json(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        "/panel/api/kb/999999/visibility",
        json={"visibility": "customer"},
        follow_redirects=False,
    )

    assert resp.status_code == 404
    assert resp.json() == {"detail": "kb document not found"}


def test_kb_set_visibility_invalid_value_400_json(client, make_user, fake_embedder):
    doc_id = _seed_doc()
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        f"/panel/api/kb/{doc_id}/visibility",
        json={"visibility": "secret"},
        follow_redirects=False,
    )

    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/json")
    assert "secret" in resp.json()["detail"]


def test_kb_set_visibility_requires_admin(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    _login(client, "oper", "oper-pass")

    resp = client.post(
        "/panel/api/kb/1/visibility",
        json={"visibility": "customer"},
        follow_redirects=False,
    )

    assert resp.status_code == 403
    assert resp.json() == {"detail": "admin role required"}


def test_kb_upload_unsupported_type_400_json(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        "/panel/api/kb",
        data={"title": "Bad"},
        files={"file": ("virus.exe", b"MZ", "application/octet-stream")},
        follow_redirects=False,
    )

    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json() == {"detail": "unsupported file type (pdf/md/csv)"}
    assert _last_audit("kb.document_ingest") is None, "failed upload must not audit"


def test_kb_upload_empty_document_400_json(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        "/panel/api/kb",
        data={"title": "Empty"},
        files={"file": ("empty.md", b"   \n  ", "text/markdown")},
        follow_redirects=False,
    )

    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json() == {"detail": "empty document"}


def test_kb_edit_creates_new_version_and_audits(client, make_user, fake_embedder):
    doc_id = _seed_doc(title="Manual", content=b"version one content")
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        f"/panel/api/kb/{doc_id}/edit",
        json={"title": "Manual v2", "content": "version two content " * 10},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"ok", "doc"}
    assert body["ok"] is True
    assert body["doc"]["id"] == doc_id
    assert body["doc"]["title"] == "Manual v2"
    assert body["doc"]["version"] == 2
    assert body["doc"]["active_version"] == 2
    # persisted + re-embedded (KB-4: new version, prior stays)
    with SessionLocal() as session:
        doc = session.get(KbDocument, doc_id)
        assert doc.version == 2
        assert doc.active_version == 2
        assert doc.active is True
        assert doc.title == "Manual v2"
    audit = _last_audit("kb.document_update")
    assert audit is not None and audit.actor == "adm"
    assert audit.before == {"version": 1}
    assert audit.after == {"version": 2, "title": "Manual v2"}


def test_kb_edit_missing_doc_404_json(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        "/panel/api/kb/999999/edit",
        json={"title": "x", "content": "y"},
        follow_redirects=False,
    )

    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json() == {"detail": "kb document not found"}


def test_kb_disable_document_audits(client, make_user, fake_embedder):
    doc_id = _seed_doc(title="Manual")
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(f"/panel/api/kb/{doc_id}/disable", follow_redirects=False)

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"ok", "doc"}
    assert body["doc"]["active"] is False
    with SessionLocal() as session:
        doc = session.get(KbDocument, doc_id)
        assert doc.active is False, "disabled doc excluded from retrieval (KB-3)"
    audit = _last_audit("kb.document_disable")
    assert audit is not None and audit.actor == "adm"
    assert audit.after == {"active": False}


def test_kb_disable_missing_doc_404_json(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post("/panel/api/kb/999999/disable", follow_redirects=False)

    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json() == {"detail": "kb document not found"}


def test_kb_enable_preserves_version_and_visibility_and_restores_retrieval(
    client, make_user, fake_embedder
):
    doc_id = _seed_doc(content=b"shared customer retrieval phrase")
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    client.post(f"/panel/api/kb/{doc_id}/visibility", json={"visibility": "customer"})
    client.post(f"/panel/api/kb/{doc_id}/disable")

    resp = client.post(f"/panel/api/kb/{doc_id}/enable", follow_redirects=False)

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"ok", "doc"}
    assert body["ok"] is True
    assert body["doc"]["active"] is True
    assert body["doc"]["active_version"] == 1
    assert body["doc"]["visibility"] == "customer"
    with SessionLocal() as session:
        doc = session.get(KbDocument, doc_id)
        assert doc.active is True
        assert doc.active_version == 1
        assert doc.visibility.value == "customer"
    search = client.get("/panel/api/kb/search?q=shared customer retrieval phrase&min_sim=0")
    assert [item["document_id"] for item in search.json()["results"]] == [doc_id]
    audit = _last_audit("kb.document_enable")
    assert audit is not None and audit.actor == "adm"
    assert audit.after == {"active": True}


def test_kb_enable_missing_doc_404_json(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post("/panel/api/kb/999999/enable", follow_redirects=False)

    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json() == {"detail": "kb document not found"}


def test_kb_restore_previous_version_audits(client, make_user, fake_embedder):
    doc_id = _seed_doc(title="Manual", content=b"v1 content")
    _seed_version2(doc_id=doc_id)
    assert _doc_version(doc_id) == 2
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        f"/panel/api/kb/{doc_id}/restore",
        json={"version": 1},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"ok", "doc"}
    assert body["doc"]["active_version"] == 1
    assert body["doc"]["active"] is True
    with SessionLocal() as session:
        doc = session.get(KbDocument, doc_id)
        assert doc.active_version == 1, "restore flips the pointer (D8), no re-embed"
        assert doc.active is True
    audit = _last_audit("kb.document_restore")
    assert audit is not None and audit.actor == "adm"
    assert audit.before == {"active_version": 2}
    assert audit.after == {"active_version": 1, "visibility": "internal"}


def test_kb_restore_customer_document_reopens_internal(client, make_user, fake_embedder):
    doc_id = _seed_doc()
    _seed_version2(doc_id=doc_id)
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    set_resp = client.post(
        f"/panel/api/kb/{doc_id}/visibility",
        json={"visibility": "customer"},
        follow_redirects=False,
    )
    assert set_resp.status_code == 200

    resp = client.post(
        f"/panel/api/kb/{doc_id}/restore",
        json={"version": 1},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    assert resp.json()["doc"]["visibility"] == "internal"


def test_kb_restore_invalid_version_400_json(client, make_user, fake_embedder):
    doc_id = _seed_doc(title="Manual")
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        f"/panel/api/kb/{doc_id}/restore",
        json={"version": 99},
        follow_redirects=False,
    )

    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json() == {"detail": "invalid version 99 for document 1"}


def test_kb_restore_missing_doc_404_json(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        "/panel/api/kb/999999/restore",
        json={"version": 1},
        follow_redirects=False,
    )

    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json() == {"detail": "kb document not found"}


def _doc_version(doc_id: int) -> int:
    with SessionLocal() as session:
        doc = session.get(KbDocument, doc_id)
        assert doc is not None
        return doc.version


# ---------------------------------------------------------------------------
# PDW-API / SETTINGS — GET all sections + POST per-section upsert
# ---------------------------------------------------------------------------


def test_settings_get_returns_all_sections_and_snapshot(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.get("/panel/api/settings", follow_redirects=False)

    assert resp.status_code == 200
    body = resp.json()
    # design #18 shape plus the effective standard messages.
    expected_keys = {
        "scope_rules", "keywords", "tone", "messages",
        "conversation_limit", "daily_limit", "meta_cost", "hours", "snapshot",
    }
    assert set(body.keys()) == expected_keys
    # defaults out of the box (SS-1..SS-5 defaults)
    assert body["scope_rules"] == {}
    assert body["tone"] == "cercano"
    assert set(body["messages"]) == {
        "greeting",
        "cannot_answer",
        "clarification",
        "farewell",
        "out_of_hours",
    }
    assert body["hours"] == {"timezone": "America/Santiago", "schedule": []}
    assert isinstance(body["keywords"], list) and len(body["keywords"]) > 0
    assert body["conversation_limit"] == 1.50
    assert body["daily_limit"] == 5.00
    assert body["meta_cost"] == 0.01
    # spend snapshot present (SS-4)
    snap = body["snapshot"]
    assert "date" in snap and "daily_limit" in snap and "daily_spend" in snap


def test_settings_update_scope_audited(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        "/panel/api/settings/scope",
        json={"rules": {"valores": "always_escalate", "calefont": "bot_resolve"}},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    with SessionLocal() as session:
        row = session.get(Settings, "scope_rules")
        assert row.value == {"valores": "always_escalate", "calefont": "bot_resolve"}
        assert row.updated_by is not None
    # audited (PDW-API-2: change is audited, SH-5)
    audit = _last_audit("settings.change")
    assert audit is not None and audit.actor == "adm"
    assert audit.entity_id == "scope_rules"
    assert audit.after == {"value": {"valores": "always_escalate", "calefont": "bot_resolve"}}


def test_settings_update_keywords_audited(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        "/panel/api/settings/keywords",
        json={"keywords": ["olor a gas", "fuga de gas", "huele raro"]},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    with SessionLocal() as session:
        row = session.get(Settings, "emergency.keywords")
        assert row.value == ["olor a gas", "fuga de gas", "huele raro"]
    audit = _last_audit("settings.change")
    assert audit is not None and audit.actor == "adm"
    assert audit.entity_id == "emergency.keywords"


def test_settings_update_tone_audited(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        "/panel/api/settings/tone", json={"tone": "formal"}, follow_redirects=False
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    with SessionLocal() as session:
        assert session.get(Settings, "tone.style").value == "formal"
    audit = _last_audit("settings.change")
    assert audit is not None and audit.actor == "adm"
    assert audit.entity_id == "tone.style"


def test_settings_update_invalid_tone_400_json(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    resp = client.post("/panel/api/settings/tone", json={"tone": "casual"}, follow_redirects=False)
    assert resp.status_code == 400
    assert _last_audit("settings.change") is None


def test_settings_update_messages_audited(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    value = {
        "greeting": "Hola editado",
        "cannot_answer": "No disponible",
        "clarification": "Aclara",
        "farewell": "Hasta luego",
        "out_of_hours": "Estamos cerrados",
    }
    resp = client.post("/panel/api/settings/messages", json=value, follow_redirects=False)
    assert resp.status_code == 200
    with SessionLocal() as session:
        for key, expected in value.items():
            assert session.get(Settings, f"messages.{key}").value == expected
    with SessionLocal() as session:
        audits = session.scalars(
            select(AuditLog).where(AuditLog.action == "settings.change")
        ).all()
    assert {audit.entity_id for audit in audits} == {
        f"messages.{key}" for key in value
    }
    assert all(audit.actor == "adm" for audit in audits)


def test_settings_update_hours_audited(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    value = {
        "timezone": "UTC",
        "schedule": [
            {"days": [1, 3, 5], "open": "09:00", "close": "17:00"},
            {"days": [2, 4], "open": "10:00", "close": "18:00"},
        ],
    }

    resp = client.post("/panel/api/settings/hours", json=value, follow_redirects=False)

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    with SessionLocal() as session:
        assert session.get(Settings, "hours.timezone").value == "UTC"
        assert session.get(Settings, "hours.schedule").value == value["schedule"]
        audits = session.scalars(
            select(AuditLog).where(AuditLog.action == "settings.change")
        ).all()
    assert {audit.entity_id for audit in audits} == {"hours.timezone", "hours.schedule"}
    assert all(audit.actor == "adm" for audit in audits)


@pytest.mark.parametrize(
    ("value", "key"),
    [
        (
            {"timezone": "UTC", "schedule": [{"days": [0], "open": "09:00", "close": "17:00"}]},
            "hours.schedule",
        ),
        (
            {
                "timezone": "UTC",
                "schedule": [
                    {"days": [1], "open": "09:00", "close": "17:00"},
                    {"days": [1], "open": "10:00", "close": "18:00"},
                ],
            },
            "hours.schedule",
        ),
        (
            {"timezone": "UTC", "schedule": [{"days": [1, 1], "open": "09:00", "close": "17:00"}]},
            "hours.schedule",
        ),
        (
            {"timezone": "UTC", "schedule": [{"days": [1], "open": "9:00", "close": "17:00"}]},
            "hours.schedule",
        ),
        (
            {"timezone": "UTC", "schedule": [{"days": [1], "open": "09:60", "close": "17:00"}]},
            "hours.schedule",
        ),
        (
            {"timezone": "UTC", "schedule": [{"days": [1], "open": "nueve", "close": "17:00"}]},
            "hours.schedule",
        ),
        (
            {"timezone": "UTC", "schedule": [{"days": [1], "open": "22:00", "close": "02:00"}]},
            "hours.schedule",
        ),
        ({"timezone": "UTC", "schedule": "09:00-17:00"}, "hours.schedule"),
        (
            {"timezone": "Not/A_Timezone", "schedule": [{"days": [1], "open": "09:00", "close": "17:00"}]},
            "hours.timezone",
        ),
    ],
)
def test_settings_update_hours_rejects_invalid_values_without_persisting(
    client, make_user, value, key
):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post("/panel/api/settings/hours", json=value, follow_redirects=False)

    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/json")
    # The rejection must come from the section's own validator, not from the
    # catch-all answering "unknown section". Without this the test would pass
    # whenever the section is missing, which is exactly how it passed at RED.
    assert "unknown section" not in resp.json()["detail"]
    with SessionLocal() as session:
        assert session.get(Settings, key) is None
        assert session.scalar(select(AuditLog).where(AuditLog.action == "settings.change")) is None


def test_settings_update_limits_audited(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        "/panel/api/settings/limits",
        json={"conversation_limit": 2.00, "daily_limit": 10.00},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    with SessionLocal() as session:
        assert session.get(Settings, "cost.conversation_limit").value == 2.00
        assert session.get(Settings, "cost.daily_limit").value == 10.00
    # two audited writes (one per key)
    with SessionLocal() as session:
        audits = session.scalars(
            select(AuditLog).where(AuditLog.action == "settings.change")
        ).all()
    changed_keys = {a.entity_id for a in audits}
    assert changed_keys == {"cost.conversation_limit", "cost.daily_limit"}
    assert all(a.actor == "adm" for a in audits)


def test_settings_update_negative_limit_400_json(client, make_user):
    """Limit validation mirrors the Jinja _number guard (SS-3): >= 0."""
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        "/panel/api/settings/limits",
        json={"conversation_limit": -1.0, "daily_limit": 5.00},
        follow_redirects=False,
    )

    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/json")
    assert "conversation_limit" in resp.json()["detail"]
    assert _last_audit("settings.change") is None, "invalid limit must not audit"


def test_settings_update_meta_audited(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        "/panel/api/settings/meta",
        json={"service_message_cost": 0.025},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    with SessionLocal() as session:
        row = session.get(Settings, "meta_pricing")
        assert row.value == {"service_message_cost": 0.025}
    audit = _last_audit("settings.change")
    assert audit is not None and audit.actor == "adm"
    assert audit.entity_id == "meta_pricing"


def test_settings_update_unknown_section_400_json(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)

    resp = client.post(
        "/panel/api/settings/unknown",
        json={},
        follow_redirects=False,
    )

    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/json")
    assert "unknown section" in resp.json()["detail"]
    assert _last_audit("settings.change") is None, "unknown section must not audit"
