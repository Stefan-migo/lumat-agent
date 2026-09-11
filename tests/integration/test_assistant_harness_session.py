"""Rolling-session and DB-authoritative recovery contracts."""

from types import SimpleNamespace

from app.chat.assistant.recovery import recover_events
from app.services.agent_chat import compact_session


def test_compaction_flushes_at_threshold_and_retains_newest_2000_tokens(monkeypatch):
    flushed = {}

    def flush(session, thread_id, *, before_tokens, after_tokens):
        flushed.update(before_tokens=before_tokens, after_tokens=after_tokens)
        return {"thread_id": thread_id, "flushed": True, "before_tokens": before_tokens}

    monkeypatch.setattr("app.services.agent_chat.flush_panel_session", flush)
    messages = [
        SimpleNamespace(id=1, content="x" * 8000),
        SimpleNamespace(id=2, content="new " * 1800),
    ]

    result = compact_session("db", 7, messages, before_tokens=4_000)

    assert result["flushed"] is True
    assert flushed == {"before_tokens": 4_000, "after_tokens": 2_000}
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


def test_compaction_records_rotation_metadata():
    result = compact_session(
        "db", 11, [SimpleNamespace(id=4, content="z" * 9000)], before_tokens=4_000
    )

    assert result["rotated"] is True
    assert result["rotation"]["thread_id"] == 11
    assert result["rotation"]["retention_tokens"] == 2_000
    assert result["rotation"]["rotated_at"]
