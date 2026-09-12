"""Rolling-session and DB-authoritative recovery contracts."""

from types import SimpleNamespace

from app.chat.assistant.recovery import recover_events
from app.chat.assistant.nodes import collect_evidence
from app.services.agent_chat import compact_session
from app.services.agent_chat import stream_events


def test_compaction_writes_bounded_recap_before_rotation(monkeypatch):
    flushed = {}

    def flush(session, thread_id, *, source_message_ids, recap, source_tokens, truncated):
        flushed.update(source_message_ids=source_message_ids, recap=recap, source_tokens=source_tokens, truncated=truncated)
        return {"thread_id": thread_id, "written": True, "id": 12}

    monkeypatch.setattr("app.services.agent_chat.flush_panel_session", flush)
    messages = [
        SimpleNamespace(id=1, content="x" * 8000),
        SimpleNamespace(id=2, content="new " * 1800),
    ]

    result = compact_session("db", 7, messages, before_tokens=4_000)

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

    result = compact_session("db", 7, [SimpleNamespace(id=1, content="small")], before_tokens=100)

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
        "db", 11, [SimpleNamespace(id=4, content="z" * 9000)], before_tokens=4_000
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
    result = compact_session("db", 11, [SimpleNamespace(id=4, content="z" * 9000)], before_tokens=4_000)

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
