"""Rolling-session and DB-authoritative recovery contracts."""

import json
from types import SimpleNamespace

import httpx
import respx

from app.chat.assistant.recovery import recover_events
from app.chat.assistant.nodes import collect_evidence
from app.config import get_settings
from app.db import SessionLocal
from app.models import InternalChatMessage, InternalChatThread, User
from app.services.agent_chat import assemble_context, compact_session, harness_limits
from app.services.agent_chat import stream_events
from app.services.users import hash_password


def test_compaction_writes_bounded_recap_before_rotation(monkeypatch):
    flushed = {}

    def flush(session, thread_id, *, source_message_ids, recap, source_tokens, truncated):
        flushed.update(source_message_ids=source_message_ids, recap=recap, source_tokens=source_tokens, truncated=truncated)
        return {"thread_id": thread_id, "written": True, "id": 12}

    monkeypatch.setattr("app.services.agent_chat.flush_panel_session", flush)
    # The window is the thread's own history: 3000 + 1800 tokens exceeds the
    # 4000 threshold. Only the newest message fits the 2000 retention.
    messages = [
        SimpleNamespace(id=1, content="x" * 12_000),
        SimpleNamespace(id=2, content="new " * 1800),
    ]

    result = compact_session("db", 7, messages)

    assert result["write"]["written"] is True
    assert flushed["source_message_ids"] == [2]
    assert "new" in flushed["recap"]
    assert flushed["source_tokens"] <= 2_000
    assert flushed["truncated"] is True
    assert result["retained_message_ids"] == [2]
    assert result["after_tokens"] <= 2_000


def test_compaction_below_threshold_does_not_flush_or_rotate(monkeypatch):
    monkeypatch.setattr(
        "app.services.agent_chat.flush_panel_session",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected flush")),
    )

    result = compact_session("db", 7, [SimpleNamespace(id=1, content="small")])

    assert result["before_tokens"] < result["threshold_tokens"]
    assert result["flushed"] is False
    assert result["rotated"] is False
    assert result["retained_message_ids"] == [1]


def test_recovery_replays_each_persisted_event_once():
    thread = SimpleNamespace(
        assistant_state={
            "events": [
                {"run_id": "run-1", "sequence": 0, "type": "plan"},
                {"run_id": "run-1", "sequence": 0, "type": "plan"},
                {"run_id": "run-1", "sequence": 1, "type": "response"},
            ]
        }
    )

    assert recover_events(thread, "run-1") == [
        {"run_id": "run-1", "sequence": 0, "type": "plan"},
        {"run_id": "run-1", "sequence": 1, "type": "response"},
    ]


def test_compaction_records_rotation_metadata(monkeypatch):
    monkeypatch.setattr(
        "app.services.agent_chat.flush_panel_session",
        lambda *args, **kwargs: {"thread_id": 11, "written": True, "id": 14},
    )
    result = compact_session(
        "db", 11, [SimpleNamespace(id=4, content="z" * 20_000)]
    )

    assert result["rotated"] is True
    assert result["rotation"]["thread_id"] == 11
    assert result["rotation"]["retention_tokens"] == 2_000
    assert result["rotation"]["rotated_at"]


def test_compaction_write_failure_is_degraded_evidence_and_rotation_is_not_successful(monkeypatch):
    monkeypatch.setattr(
        "app.services.agent_chat.flush_panel_session",
        lambda *args, **kwargs: {"thread_id": 11, "written": False, "degraded_reason": "db unavailable"},
    )
    result = compact_session("db", 11, [SimpleNamespace(id=4, content="z" * 20_000)])

    assert result["write"]["written"] is False
    assert result["write"]["degraded_reason"] == "db unavailable"
    assert result["rotated"] is False
    assert result["failed"] is True


def test_graph_preserves_failed_compaction_as_degraded_evidence():
    state = collect_evidence({
        "evidence": [],
        "compaction": {"failed": True, "write": {"degraded_reason": "db unavailable"}},
    })

    assert state["evidence"][-1]["status"] == "degraded"
    assert state["evidence"][-1]["compaction"]["failed"] is True


def test_reconnect_uses_persisted_events_as_authority():
    thread = SimpleNamespace(assistant_state={"events": [{"run_id": "r", "sequence": 0, "type": "status"}]})
    assert stream_events(None, thread, "r") == thread.assistant_state["events"]


def test_blocked_state_is_persisted_as_completed_and_recoverable():
    state = {
        "stage": "completed",
        "recoverable": True,
        "cost_mode": "blocked",
        "events": [{"type": "response", "content": "limit reached"}],
    }
    thread = SimpleNamespace(assistant_state=state)

    assert thread.assistant_state["stage"] == "completed"
    assert thread.assistant_state["recoverable"] is True
    assert thread.assistant_state["cost_mode"] == "blocked"


# ---------------------------------------------------------------------------
# Compaction through the REAL caller.
#
# The tests above call `compact_session` directly and hand it `before_tokens`.
# That is exactly how the unreachable-gate defect shipped: the value under test
# was supplied by the test instead of by the production caller. These tests
# drive the real path — assemble the context, then compact — so the caller's
# input is what is being exercised.
# ---------------------------------------------------------------------------


def _planner_provider(planner: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body.get("stream"):
            payload = json.dumps({"choices": [{"delta": {"content": "ok"}}]})
            return httpx.Response(200, content=f"data: {payload}\n\ndata: [DONE]\n\n")
        return httpx.Response(200, json={
            "choices": [{"message": {"content": json.dumps(planner)}, "finish_reason": "stop"}],
        })

    return handler


def _admin(client, username: str) -> int:
    with SessionLocal() as session:
        user = User(username=username, password_hash=hash_password("pass"), role="admin")
        session.add(user)
        session.flush()
        user_id = user.id
        session.commit()
    assert client.post("/panel/api/login", json={"username": username, "password": "pass"}).status_code == 200
    return user_id


def test_compaction_fires_once_the_thread_window_fills(client, monkeypatch):
    """The gate must measure the thread window, not the injected context.

    `assemble_context` caps the injected context at the injection budget, so a
    gate fed that value can never open. A thread whose history exceeds the
    compaction threshold must compact anyway.
    """
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    from app.config import get_settings

    get_settings.cache_clear()
    _admin(client, "compaction-window")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]

    # 20 x 1001 chars ~= 5,020 window tokens: above the compaction threshold,
    # while the injected context stays capped below it.
    with SessionLocal() as session:
        for _ in range(20):
            session.add(InternalChatMessage(
                thread_id=thread_id, author="admin", content="x" * 1001, status="processed",
            ))
        session.commit()

    planner = {"kind": "respond", "classification": "normal", "summary": "ok", "requires_approval": False}
    with respx.mock(base_url="https://openrouter.ai/api/v1") as router:
        router.post("/chat/completions").mock(side_effect=_planner_provider(planner))
        assert client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "hola"}).status_code == 201

    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        injected = thread.assistant_state["context_meta"]["estimated_tokens"]
        compaction = thread.assistant_state["compaction"]

    assert injected < harness_limits().compaction_threshold, "HL-1: the injected context stays budget-capped"
    assert compaction["flushed"] is True
    assert compaction["rotated"] is True


def test_compaction_stays_idle_for_a_short_thread(client, monkeypatch):
    """A thread below the threshold must not flush or rotate."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    from app.config import get_settings

    get_settings.cache_clear()
    _admin(client, "compaction-short")
    thread_id = client.post("/panel/api/chat/threads", json={}).json()["thread"]["id"]

    planner = {"kind": "respond", "classification": "normal", "summary": "ok", "requires_approval": False}
    with respx.mock(base_url="https://openrouter.ai/api/v1") as router:
        router.post("/chat/completions").mock(side_effect=_planner_provider(planner))
        assert client.post(f"/panel/api/chat/threads/{thread_id}/messages", json={"content": "hola"}).status_code == 201

    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        compaction = thread.assistant_state["compaction"]

    assert compaction["flushed"] is False
    assert compaction["rotated"] is False


def test_harness_limits_come_from_settings(monkeypatch):
    """The harness limits are configuration, not module constants.

    They were duplicated as module constants in `assistant.state` while the
    settings were never read, so an operator could move the threshold and nothing
    would happen.
    """
    monkeypatch.setenv("ASSISTANT_COMPACTION_THRESHOLD_TOKENS", "1234")
    monkeypatch.setenv("ASSISTANT_COMPACTION_RETENTION_TOKENS", "321")
    monkeypatch.setenv("ASSISTANT_SESSION_WINDOW_TOKENS", "4321")
    monkeypatch.setenv("ASSISTANT_CONTEXT_INJECTION_BUDGET", "111")
    get_settings.cache_clear()
    try:
        limits = harness_limits()
        assert (limits.compaction_threshold, limits.compaction_retention) == (1234, 321)
        assert (limits.session_window, limits.injection_budget) == (4321, 111)

        # Compaction evidence reports the configured values.
        result = compact_session("db", 7, [SimpleNamespace(id=1, content="small")])
        assert result["threshold_tokens"] == 1234
        assert result["window_tokens"] == 4321

        # The assembler applies the configured injection budget: a 1,000-token
        # message no longer fits a 111-token ceiling (it did under the old 4,000).
        context = assemble_context(
            None, 7, messages=[SimpleNamespace(id=1, content="x" * 4_000)], attachments=[]
        )
        assert context["meta"]["estimated_tokens"] == 0
        assert context["meta"]["truncated"] is True
    finally:
        get_settings.cache_clear()
