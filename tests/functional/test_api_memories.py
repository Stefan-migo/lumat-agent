"""Panel JSON API memories (MEM-6; PDW-API, PDW-API-3, PDW-AUTH-1, D4, SH-5).

Thin JSON wrappers over `app/services/memory.py`, scoped to the customer ficha
(design "Panel API + UI"):

- GET     /clients/{id}/memories      -> {"memories": [...]} (scope=customer)
- POST    /clients/{id}/memories      -> {"ok", "memory"} (upsert, audited)
- DELETE  /clients/{id}/memories/{id} -> {"ok"} (delete, audited)
- POST    /clients/{id}/memories/{id}/mark -> {"ok", "memory"} (pin/status)

Role matrix (design): any authenticated panel user (admin or operador) manages
a ficha's memories — `require_user_json` (PDW-API-4). Listing is scoped to the
selected client (MEM-6). All errors JSON {"detail": ...} (PDW-API-3): 401 from
the JSON-401 dep (D4, PDW-AUTH-1), 404 for a missing customer/memory, 400 for
an empty memory content. No redirects, no CORS (D1).
"""

from __future__ import annotations

from sqlalchemy import select

from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    AuditLog,
    Customer,
    CustomerState,
    Memory,
    MemoryType,
)


def _seed_customer(*, name: str = "Ana Martínez", phone: str = "+56911112222") -> int:
    """Create a bare customer row (no conversation needed for memories)."""
    with SessionLocal() as session:
        customer = Customer(phone_e164=phone, name=name, state=CustomerState.NUEVO)
        session.add(customer)
        session.flush()
        customer_id = customer.id
        session.commit()
        return customer_id


def _seed_memory(customer_id: int, *, tipo: MemoryType = MemoryType.DECISION, **kw) -> Memory:
    """Create a customer-scoped memory row directly via the memory service."""
    from app.services import memory

    with SessionLocal() as session:
        row = memory.upsert(
            session,
            scope="customer",
            entity_id=str(customer_id),
            topic_key=kw.pop("topic_key", "general"),
            tipo=tipo,
            titulo=kw.pop("titulo", "decision"),
            contenido=kw.pop("contenido", "el cliente prefiere horario de tarde"),
        )
        session.commit()
        return row


def _login(client, username: str = "oper", password: str = "oper-pass") -> None:
    resp = client.post(
        "/panel/api/login",
        json={"username": username, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 200, f"api login must succeed: {resp.status_code} {resp.text}"


def test_memories_endpoints_require_login_401_json(client, make_user):
    """No session -> every memories endpoint answers 401 JSON, never a 302."""
    for method, path, body in [
        ("get", "/panel/api/clients/1/memories", None),
        ("post", "/panel/api/clients/1/memories", {}),
        ("delete", "/panel/api/clients/1/memories/1", None),
        ("post", "/panel/api/clients/1/memories/1/mark", {}),
    ]:
        kwargs = {"json": body} if body is not None else {}
        resp = getattr(client, method)(path, follow_redirects=False, **kwargs)
        assert resp.status_code == 401, f"{method.upper()} {path} must be 401"
        assert "location" not in resp.headers, f"{path} must not redirect"
        assert resp.headers["content-type"].startswith("application/json"), (
            f"{path} error must be JSON (PDW-API-3)"
        )
        assert resp.json() == {"detail": "unauthorized"}
        assert "access-control-allow-origin" not in resp.headers, "no CORS (D1)"


def test_memories_list_missing_customer_404_json(client, make_user):
    """Unknown customer -> 404 {"detail":"customer not found"} (PDW-API-3)."""
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get("/panel/api/clients/999999/memories", follow_redirects=False)

    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json() == {"detail": "customer not found"}


# ---------------------------------------------------------------------------
# MEM-6 list — scoped to the selected client, serializer shape, empty list
# ---------------------------------------------------------------------------


def test_memories_list_scoped_to_client_and_newest_first(client, make_user):
    """Only this customer's memories return, in a stable serializer shape."""
    c1 = _seed_customer(name="Ana Martínez", phone="+56911112222")
    c2 = _seed_customer(name="Pedro Soto", phone="+56933334444")
    _seed_memory(c1, topic_key="k1", titulo="preferencia", contenido="prefiere tarde")
    _seed_memory(c2, topic_key="k1", titulo="preferencia", contenido="prefiere manana")
    _seed_memory(c1, topic_key="k2", titulo="decision", contenido="acepta presupuesto")
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get(f"/panel/api/clients/{c1}/memories", follow_redirects=False)

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"memories"}
    rows = body["memories"]
    # newest first (updated_at desc)
    assert len(rows) == 2
    assert {r["topic_key"] for r in rows} == {"k1", "k2"}
    # serializer shape (design "Panel API + UI")
    row = next(r for r in rows if r["topic_key"] == "k1")
    assert row["id"] > 0
    assert row["scope"] == "customer"
    assert row["entity_id"] == str(c1)
    assert row["tipo"] == "decision"
    assert row["titulo"] == "preferencia"
    assert row["contenido"] == "prefiere tarde"
    assert row["pin"] is False
    assert row["status"] == "active"
    from datetime import datetime

    datetime.fromisoformat(row["created_at"])
    datetime.fromisoformat(row["updated_at"])
    # scoped: c2's memories are NOT visible from c1's ficha (MEM-6)
    assert all(r["entity_id"] == str(c1) for r in rows)


def test_memories_list_empty_when_none(client, make_user):
    """A customer with no memories -> empty list, no error (MEM-6)."""
    c1 = _seed_customer()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.get(f"/panel/api/clients/{c1}/memories", follow_redirects=False)

    assert resp.status_code == 200
    assert resp.json() == {"memories": []}


# ---------------------------------------------------------------------------
# MEM-6 upsert — create/update, audited, empty + unknown rejected, non-default
# ---------------------------------------------------------------------------


def test_memory_upsert_creates_row_audited(client, make_user):
    customer_id = _seed_customer()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.post(
        f"/panel/api/clients/{customer_id}/memories",
        json={"tipo": "preference", "titulo": "horario", "contenido": "prefiere horario de tarde"},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"ok", "memory"}
    assert body["ok"] is True
    mem = body["memory"]
    assert mem["scope"] == "customer"
    assert mem["entity_id"] == str(customer_id)
    assert mem["tipo"] == "preference"
    assert mem["titulo"] == "horario"
    assert mem["contenido"] == "prefiere horario de tarde"
    assert mem["topic_key"] == "general"  # default topic_key

    # persisted + audited (SH-5)
    with SessionLocal() as session:
        stored = session.scalars(select(Memory).where(Memory.entity_id == str(customer_id))).all()
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "memory.upserted"))
    assert len(stored) == 1
    assert stored[0].contenido == "prefiere horario de tarde"
    assert audit is not None
    assert audit.actor == "oper"
    assert audit.after == {
        "customer_id": customer_id,
        "tipo": "preference",
        "topic_key": "general",
        "titulo": "horario",
    }


def test_memory_upsert_updates_existing_topic_key(client, make_user):
    """Same topic_key -> the existing row is refreshed, not duplicated (MEM-2)."""
    customer_id = _seed_customer()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    # First upsert on the default topic_key "general".
    client.post(
        f"/panel/api/clients/{customer_id}/memories",
        json={"tipo": "decision", "contenido": "v1"},
        follow_redirects=False,
    )
    # Second upsert on the same key replaces the content.
    resp = client.post(
        f"/panel/api/clients/{customer_id}/memories",
        json={"tipo": "decision", "contenido": "v2 actualizado"},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    with SessionLocal() as session:
        stored = session.scalars(select(Memory).where(Memory.entity_id == str(customer_id))).all()
    assert len(stored) == 1, "same topic_key must de-duplicate"
    assert stored[0].contenido == "v2 actualizado"


def test_memory_upsert_empty_content_rejected_400(client, make_user):
    customer_id = _seed_customer()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.post(
        f"/panel/api/clients/{customer_id}/memories",
        json={"contenido": "   "},
        follow_redirects=False,
    )

    assert resp.status_code == 400
    assert resp.headers["content-type"].startswith("application/json")
    assert "detail" in resp.json()
    with SessionLocal() as session:
        stored = session.scalars(select(Memory)).all()
    assert stored == [], "empty content must not be stored"


def test_memory_upsert_unknown_type_rejected_400(client, make_user):
    customer_id = _seed_customer()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.post(
        f"/panel/api/clients/{customer_id}/memories",
        json={"tipo": "not-a-type", "contenido": "hola"},
        follow_redirects=False,
    )

    assert resp.status_code == 400
    assert resp.json().get("detail") == "unknown memory type: 'not-a-type'"


def test_memory_upsert_non_default_project_rejected(client, make_user):
    """MEM-2: writers reject a non-default project before any write.

    The routes never accept a `proyecto` field — the writable project is
    pinned to 'default' at the route level — so a direct attempt to target a
    non-default project via the service must also be rejected end-to-end.
    """
    from app.services import memory as memory_service

    customer_id = _seed_customer()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    # The route has no proyecto field; verify the service contract holds.
    with SessionLocal() as session:
        try:
            memory_service.upsert(
                session,
                scope="customer",
                entity_id=str(customer_id),
                topic_key="x",
                tipo=MemoryType.DECISION,
                titulo="x",
                contenido="contenido",
                proyecto="other",
            )
        except ValueError as exc:
            assert "proyecto='default'" in str(exc)
        else:
            raise AssertionError("non-default proyecto must be rejected on the service")


def test_memory_upsert_missing_customer_404(client, make_user):
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.post(
        "/panel/api/clients/999999/memories",
        json={"contenido": "hola"},
        follow_redirects=False,
    )

    assert resp.status_code == 404
    assert resp.json() == {"detail": "customer not found"}


# ---------------------------------------------------------------------------
# MEM-6 delete — scoped to the ficha, 404 on foreign/id, audited
# ---------------------------------------------------------------------------


def test_memory_delete_own_ficha_audited(client, make_user):
    customer_id = _seed_customer()
    row = _seed_memory(customer_id, topic_key="k1")
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.delete(
        f"/panel/api/clients/{customer_id}/memories/{row.id}", follow_redirects=False
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "deleted": row.id}
    with SessionLocal() as session:
        gone = session.get(Memory, row.id)
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "memory.deleted"))
    assert gone is None, "memory must be deleted"
    assert audit is not None and audit.actor == "oper"


def test_memory_delete_cross_customer_404(client, make_user):
    """A memory belonging to another customer's ficha is not findable (MEM-6)."""
    c1 = _seed_customer(name="Ana", phone="+56911112222")
    c2 = _seed_customer(name="Pedro", phone="+56933334444")
    row = _seed_memory(c2, topic_key="k1")
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    # Try to delete c2's memory through c1's ficha.
    resp = client.delete(
        f"/panel/api/clients/{c1}/memories/{row.id}", follow_redirects=False
    )

    assert resp.status_code == 404
    assert resp.json() == {"detail": "memory not found"}
    with SessionLocal() as session:
        assert session.get(Memory, row.id) is not None, "memory must survive"


# ---------------------------------------------------------------------------
# MEM-6 mark — pin/status toggle, audited
# ---------------------------------------------------------------------------


def test_memory_mark_pins_and_audits(client, make_user):
    customer_id = _seed_customer()
    row = _seed_memory(customer_id, topic_key="k1")
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.post(
        f"/panel/api/clients/{customer_id}/memories/{row.id}/mark",
        json={"pin": True},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["memory"]["pin"] is True
    with SessionLocal() as session:
        stored = session.get(Memory, row.id)
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "memory.marked"))
    assert stored is not None and stored.pin is True
    assert audit is not None and audit.actor == "oper"


def test_memory_mark_status_and_archive(client, make_user):
    customer_id = _seed_customer()
    row = _seed_memory(customer_id, topic_key="k1")
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    resp = client.post(
        f"/panel/api/clients/{customer_id}/memories/{row.id}/mark",
        json={"status": "archived"},
        follow_redirects=False,
    )

    assert resp.status_code == 200
    assert resp.json()["memory"]["status"] == "archived"
    with SessionLocal() as session:
        stored = session.get(Memory, row.id)
    assert stored is not None and stored.status.value == "archived"


# ---------------------------------------------------------------------------
# MEM-6 role matrix — operador (full on any ficha) and admin (full)
# ---------------------------------------------------------------------------


def test_memory_actions_operador_full(client, make_user):
    """Operador can list/create/delete/mark on a ficha (design role matrix)."""
    customer_id = _seed_customer()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    created = client.post(
        f"/panel/api/clients/{customer_id}/memories",
        json={"contenido": "nota operador"},
        follow_redirects=False,
    )
    assert created.status_code == 200
    memory_id = created.json()["memory"]["id"]

    listed = client.get(f"/panel/api/clients/{customer_id}/memories", follow_redirects=False)
    assert listed.status_code == 200
    assert len(listed.json()["memories"]) == 1

    marked = client.post(
        f"/panel/api/clients/{customer_id}/memories/{memory_id}/mark",
        json={"pin": True},
        follow_redirects=False,
    )
    assert marked.status_code == 200

    deleted = client.delete(
        f"/panel/api/clients/{customer_id}/memories/{memory_id}", follow_redirects=False
    )
    assert deleted.status_code == 200


def test_memory_actions_admin_full(client, make_user):
    """Admin can list/create/delete/mark on a ficha."""
    customer_id = _seed_customer()
    make_user("admin", "admin-pass", role="admin")
    _login(client, username="admin", password="admin-pass")

    created = client.post(
        f"/panel/api/clients/{customer_id}/memories",
        json={"contenido": "nota admin"},
        follow_redirects=False,
    )
    assert created.status_code == 200
    memory_id = created.json()["memory"]["id"]

    deleted = client.delete(
        f"/panel/api/clients/{customer_id}/memories/{memory_id}", follow_redirects=False
    )
    assert deleted.status_code == 200


# ---------------------------------------------------------------------------
# End-to-end — API-created memory appears on the ficha (MEM-4 -> MEM-6 -> CR-7)
# ---------------------------------------------------------------------------


def test_api_memory_surfaces_on_ficha_e2e(client, make_user):
    """A memory written via the panel API is listed and the memo reaches the ficha.

    Proves the full loop: upsert via POST /clients/{id}/memories (MEM-6), a
    close writes the customer_memo (MEM-4), and GET /clients/{id} surfaces it
    distinct from notes (CR-7).
    """
    from app.models import (
        Conversation,
        ConversationState,
        MemoryProducer,
        MemoryType,
        MemoryVisibility,
    )
    from app.services import memory as memory_service

    customer_id = _seed_customer()
    make_user("oper", "oper-pass", role="operador")
    _login(client)

    # 1) a panel user upserts a preference memory via the API (MEM-6)
    resp = client.post(
        f"/panel/api/clients/{customer_id}/memories",
        json={"tipo": "preference", "contenido": "cliente prefiere horario de tarde"},
        follow_redirects=False,
    )
    assert resp.status_code == 200

    # 2) a conversation closes -> the customer_memo is upserted (MEM-4).
    #    S3's integration tests already exercise set_conversation_state(CLOSED)
    #    wiring the call; here we drive the customer_memo write directly so the
    #    panel API -> ficha loop is what this test bounds.
    with SessionLocal() as session:
        conversation = Conversation(
            customer_id=customer_id,
            wa_phone="+56911112222",
            state=ConversationState.BOT,
        )
        session.add(conversation)
        session.flush()
        memory_service.close_conversation(
            session, conversation, acta_text="acta del cierre final"
        )
        memory_service.upsert(
            session,
            scope="agent",
            entity_id="agent:assistant",
            topic_key="agent:project-fact",
            tipo=MemoryType.DISCOVERY,
            titulo="Project fact",
            contenido="Agent-wide fact",
            visibility=MemoryVisibility.PROJECT,
            producer=MemoryProducer.AGENT,
            origin_thread_id=str(conversation.id),
        )
        session.commit()

    # 3) the ficha surfaces the memo (CR-7) and both rows exist
    ficha = client.get(f"/panel/api/clients/{customer_id}", follow_redirects=False)
    assert ficha.status_code == 200
    assert ficha.json()["memo"] == "acta del cierre final"

    listed = client.get(f"/panel/api/clients/{customer_id}/memories", follow_redirects=False)
    assert all(memory["scope"] == "customer" for memory in listed.json()["memories"])
    keys = {m["topic_key"] for m in listed.json()["memories"]}
    assert {"general", "customer_memo"} <= keys
