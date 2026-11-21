"""Integration contracts for the approved chatbot regression measurement tool (S4)."""

import json

import pytest

from app.chat.assistant.approval import consume_approval, issue_approval
from app.chat.assistant.tools.registry import ToolValidationError, execute_tool, get_tool
from app.db import SessionLocal
from app.services.prompts import load_assistant_config

TOOL = "chatbot.eval_regression"
ARGUMENTS = {"scenarios": ["simple-saludo-variante"], "baseline_run_tag": "named-baseline"}


def _approval(arguments: dict) -> dict:
    normalized = get_tool(TOOL).args_model.model_validate(arguments).model_dump()
    approval = issue_approval({"tool": TOOL, "arguments": normalized})
    assert consume_approval(approval, approval["token"]) is True
    return approval


def _baseline_report(ev, scenario_id: str) -> dict:
    row = {
        "scenario": scenario_id,
        "tier": "simple",
        "passed": True,
        "capped": False,
        "gates_failed": [],
        "score": 2.5,
        "dimensions": {name: 2.5 for name in ev.DIMENSIONS},
    }
    return {
        "stamp": {"run_tag": "named-baseline", "corpus_fingerprint": "same-corpus"},
        "runs": [row],
    }


def _run(monkeypatch, arguments, *, approval=None):
    with SessionLocal() as session:
        return execute_tool(
            session,
            TOOL,
            arguments,
            approval=approval,
            whitelist=set(load_assistant_config().tools_whitelist),
            role="admin",
        )


def test_approved_call_returns_scores_from_the_named_baseline_report(monkeypatch, tmp_path):
    import scripts.conv_eval as ev

    scenario_id = ARGUMENTS["scenarios"][0]
    report_path = tmp_path / "conv-eval-named-baseline.json"
    report_path.write_text(json.dumps(_baseline_report(ev, scenario_id)), encoding="utf-8")
    monkeypatch.setattr(
        ev,
        "report_paths",
        lambda out_dir, tag: (report_path if tag == "named-baseline" else tmp_path / f"{tag}.json", tmp_path / "unused.md"),
    )
    observation = {
        "state": "bot",
        "events": [],
        "intents": [],
        "replies": ["Hola, soy Max de Lumat. ¿En qué te ayudo?"],
        "turns": [{"text": "hola", "replies": ["Hola, soy Max de Lumat. ¿En qué te ayudo?"], "intent": None}],
    }
    monkeypatch.setattr(
        ev, "run_scenario",
        lambda scenario, **kwargs: {"observation": observation},
    )
    monkeypatch.setattr(
        ev, "judge_row",
        lambda scenario, _observation, **kwargs: {
            "dimensions": {name: {"score": 4, "evidence": "cita"} for name in ev.DIMENSIONS},
            "hard_fail": False,
            "hard_fail_reason": "",
            "summary": "bien",
        },
    )
    import scripts.conv_eval_judge as judge
    monkeypatch.setattr(judge, "resolve_credentials", lambda: type("Credentials", (), {"source": "test"})())
    monkeypatch.setattr(judge, "build_client", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(ev, "preflight", lambda: {"fingerprint": "test-kb", "documents": 1})
    monkeypatch.setattr(ev, "kb_text", lambda: "kb")
    monkeypatch.setattr(ev, "tarifario_text", lambda: "tarifa")
    monkeypatch.setattr(ev, "miss_offer_text", lambda: "miss")
    monkeypatch.setattr(ev, "git_state", lambda **_kwargs: ("abc123", False))
    monkeypatch.setattr(ev, "_bot_settings", lambda: ("test-provider", "test-model"))

    result = _run(monkeypatch, ARGUMENTS, approval=_approval(ARGUMENTS))

    assert result["status"] == "completed"
    payload = result["result"]
    assert payload["baseline_run_tag"] == "named-baseline"
    assert payload["scenarios"][0]["before"]["score"] == 2.5
    assert payload["scenarios"][0]["after"]["score"] == 4.0
    assert payload["scenarios"][0]["moved"] is True
    assert payload["moved_scenarios"] == [scenario_id]
    assert payload["gate_failures"] == {}
    assert payload["appears_in_inbox"] is True
    assert payload["provenance"]["judge_model"] == judge.JUDGE_MODEL


@pytest.mark.parametrize("baseline_content", [None, "not json"])
def test_missing_or_unreadable_baseline_is_refused(monkeypatch, tmp_path, baseline_content):
    import scripts.conv_eval as ev

    report_path = tmp_path / "conv-eval-named-baseline.json"
    if baseline_content is not None:
        report_path.write_text(baseline_content, encoding="utf-8")
    monkeypatch.setattr(ev, "report_paths", lambda _out, _tag: (report_path, tmp_path / "unused.md"))

    result = _run(monkeypatch, ARGUMENTS, approval=_approval(ARGUMENTS))

    assert result["status"] == "error"
    assert "baseline" in result["error"].lower()


def test_missing_judge_key_reports_failure_without_gates_only_score(monkeypatch, tmp_path):
    import scripts.conv_eval as ev
    import scripts.conv_eval_judge as judge

    scenario_id = ARGUMENTS["scenarios"][0]
    report_path = tmp_path / "conv-eval-named-baseline.json"
    report_path.write_text(json.dumps(_baseline_report(ev, scenario_id)), encoding="utf-8")
    monkeypatch.setattr(ev, "report_paths", lambda _out, _tag: (report_path, tmp_path / "unused.md"))

    def unavailable():
        raise judge.JudgeKeyUnavailable("no judge credential")

    monkeypatch.setattr(judge, "resolve_credentials", unavailable)
    calls = []
    monkeypatch.setattr(ev, "run_scenario", lambda *args, **kwargs: calls.append((args, kwargs)))

    result = _run(monkeypatch, ARGUMENTS, approval=_approval(ARGUMENTS))

    assert result["status"] == "error"
    assert "judge" in result["error"].lower()
    assert "credential" in result["error"].lower()
    assert calls == []
    assert "result" not in result


def test_call_without_approval_is_refused_before_running(monkeypatch):
    import scripts.conv_eval as ev

    calls = []
    monkeypatch.setattr(ev, "run_scenario", lambda *args, **kwargs: calls.append((args, kwargs)))
    with SessionLocal() as session:
        with pytest.raises(ToolValidationError, match="requires consumed exact approval"):
            execute_tool(
                session,
                TOOL,
                ARGUMENTS,
                whitelist=set(load_assistant_config().tools_whitelist),
                role="admin",
            )
    assert calls == []
