"""Model-free contracts for the rubric judge and the simulated customer.

`scripts/conv_eval_judge.py` is the only piece of the evaluation that talks to a
language model, so it cannot be part of a deterministic suite. What *is* pinned
here is the part that decides whether a score is trusted at all:

- **the verdict contract** (`validate_verdict`): six dimensions, integer 0-4,
  evidence and a boolean hard fail. A judge that cannot produce exactly this
  produced no verdict, and no verdict is never reported as a passing one.
- **credential resolution** (`resolve_credentials`): the order, and the fact
  that a missing key raises instead of silently scoring nothing.

No network call happens here: `_chat` is never reached.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import conv_eval_judge as judge  # noqa: E402


def verdict(**overrides):
    dimensions = {name: {"score": 3, "evidence": "cita textual"} for name in judge.DIMENSIONS}
    payload = {
        "dimensions": dimensions,
        "hard_fail": False,
        "hard_fail_reason": "",
        "summary": "resumen",
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Verdict contract
# ---------------------------------------------------------------------------


def test_a_valid_verdict_passes_through_every_dimension():
    clean = judge.validate_verdict(verdict())
    assert set(clean["dimensions"]) == set(judge.DIMENSIONS)
    assert clean["dimensions"]["grounding"] == {"score": 3, "evidence": "cita textual"}
    assert clean["hard_fail"] is False


def test_optional_strings_default_to_empty():
    clean = judge.validate_verdict({"dimensions": verdict()["dimensions"], "hard_fail": True})
    assert clean["hard_fail"] is True
    assert clean["hard_fail_reason"] == ""
    assert clean["summary"] == ""


def test_missing_dimension_is_refused_by_name():
    payload = verdict()
    del payload["dimensions"]["closure"]
    with pytest.raises(judge.JudgeError) as raised:
        judge.validate_verdict(payload)
    assert "closure" in str(raised.value)


@pytest.mark.parametrize("score", [-1, 5, 3.0, "3", True, None])
def test_invalid_scores_are_refused(score):
    payload = verdict()
    payload["dimensions"]["tone"]["score"] = score
    with pytest.raises(judge.JudgeError) as raised:
        judge.validate_verdict(payload)
    assert "tone" in str(raised.value)


def test_dimensions_must_be_a_mapping():
    with pytest.raises(judge.JudgeError):
        judge.validate_verdict({"dimensions": ["grounding"], "hard_fail": False})


@pytest.mark.parametrize("hard_fail", [None, "no", 0, 1])
def test_hard_fail_must_be_a_real_boolean(hard_fail):
    with pytest.raises(judge.JudgeError):
        judge.validate_verdict(verdict(hard_fail=hard_fail))


def test_unknown_dimensions_are_dropped_not_reported_as_graded():
    payload = verdict()
    payload["dimensions"]["inventada"] = {"score": 4, "evidence": "x"}
    clean = judge.validate_verdict(payload)
    assert "inventada" not in clean["dimensions"]


# ---------------------------------------------------------------------------
# Credential resolution — order, and never a silent absence
# ---------------------------------------------------------------------------


def test_an_explicit_key_wins_and_is_labelled(tmp_path, monkeypatch):
    monkeypatch.setenv("EVAL_JUDGE_API_KEY", "desde-el-entorno")
    credentials = judge.resolve_credentials("explicita")
    assert credentials.api_key == "explicita"
    assert credentials.source == "argument"


def test_the_environment_variable_is_second(monkeypatch):
    monkeypatch.setenv("EVAL_JUDGE_API_KEY", "desde-el-entorno")
    credentials = judge.resolve_credentials()
    assert credentials.api_key == "desde-el-entorno"
    assert credentials.source == "EVAL_JUDGE_API_KEY"


def test_a_missing_credential_raises_and_names_the_way_out(tmp_path, monkeypatch):
    monkeypatch.delenv("EVAL_JUDGE_API_KEY", raising=False)
    monkeypatch.setattr(judge, "SHELL_AUTH_PATH", tmp_path / "ausente.json")
    with pytest.raises(judge.JudgeKeyUnavailable) as raised:
        judge.resolve_credentials()
    assert "EVAL_JUDGE_API_KEY" in str(raised.value)


def test_the_shell_auth_file_is_the_last_resort(tmp_path, monkeypatch):
    monkeypatch.delenv("EVAL_JUDGE_API_KEY", raising=False)
    auth = tmp_path / "auth.json"
    auth.write_text('{"opencode-go": {"key": "desde-auth"}}', encoding="utf-8")
    monkeypatch.setattr(judge, "SHELL_AUTH_PATH", auth)
    credentials = judge.resolve_credentials()
    assert credentials.api_key == "desde-auth"
    assert "opencode-go" in credentials.source


def test_an_empty_key_in_the_auth_file_is_refused(tmp_path, monkeypatch):
    monkeypatch.delenv("EVAL_JUDGE_API_KEY", raising=False)
    auth = tmp_path / "auth.json"
    auth.write_text('{"opencode-go": {"key": ""}}', encoding="utf-8")
    monkeypatch.setattr(judge, "SHELL_AUTH_PATH", auth)
    with pytest.raises(judge.JudgeKeyUnavailable):
        judge.resolve_credentials()


# ---------------------------------------------------------------------------
# Transport — the gateway refuses a request that does not identify its session
# ---------------------------------------------------------------------------


def test_build_client_sends_a_stable_session_and_names_itself():
    client = judge.build_client(
        judge.JudgeCredentials("clave", "argument"), session_id="conv-eval-smoke"
    )
    assert client.default_headers["x-opencode-session"] == "conv-eval-smoke"
    assert client.default_headers["user-agent"] == "lumat-conv-eval/1.0"


def test_build_client_invents_a_session_when_none_is_given():
    first = judge.build_client(judge.JudgeCredentials("clave", "argument"))
    second = judge.build_client(judge.JudgeCredentials("clave", "argument"))
    assert first.default_headers["x-opencode-session"]
    assert first.default_headers["x-opencode-session"] != second.default_headers["x-opencode-session"]


# ---------------------------------------------------------------------------
# Retry — a truncated answer is a transport accident, not a verdict
# ---------------------------------------------------------------------------


def fake_chat(responses):
    calls = []

    def _chat(client, messages, model=None):
        calls.append(messages)
        return responses[min(len(calls) - 1, len(responses) - 1)]

    return _chat, calls


def test_a_malformed_answer_is_retried_once(monkeypatch):
    valid = (
        '{"dimensions": {'
        + ", ".join(f'"{name}": {{"score": 3, "evidence": "cita"}}' for name in judge.DIMENSIONS)
        + '}, "hard_fail": false}'
    )
    chat, calls = fake_chat(["{\"dimensions\": {\"grounding\": {\"score\": 4", valid])
    monkeypatch.setattr(judge, "_chat", chat)
    verdict = judge.judge_conversation(
        object(), transcript=[], scenario={"id": "x"}, kb_text="", tarifario=""
    )
    assert len(calls) == 2
    assert verdict["dimensions"]["tone"]["score"] == 3


def test_two_malformed_answers_raise_instead_of_guessing(monkeypatch):
    chat, calls = fake_chat(["no es json", "tampoco"])
    monkeypatch.setattr(judge, "_chat", chat)
    with pytest.raises(judge.JudgeError) as raised:
        judge.judge_conversation(
            object(), transcript=[], scenario={"id": "x"}, kb_text="", tarifario=""
        )
    assert len(calls) == 2
    assert "2 attempts" in str(raised.value)


# ---------------------------------------------------------------------------
# Simulated customer — it plays the customer and never the assistant
# ---------------------------------------------------------------------------


def test_the_simulator_is_told_it_is_not_the_assistant(monkeypatch):
    chat, calls = fake_chat(['{"message": "hola necesito ayuda", "goal_reached": false}'])
    monkeypatch.setattr(judge, "_chat", chat)

    judge.simulate_customer_turn(
        object(),
        persona="Cliente enojado, escribe en mayúsculas",
        goal="Que alguien se haga cargo del reclamo",
        transcript=[{"role": "customer", "text": "hola"}],
        turn_index=2,
        max_turns=5,
    )

    system = calls[0][0]["content"]
    assert "NOT the assistant" in system
    assert "never write as one" in system
    assert "Never narrate actions" in system


def test_the_simulator_stops_when_the_goal_is_reached(monkeypatch):
    chat, _calls = fake_chat(['{"message": "", "goal_reached": true}'])
    monkeypatch.setattr(judge, "_chat", chat)

    simulated = judge.simulate_customer_turn(
        object(),
        persona="cliente",
        goal="saludar",
        transcript=[{"role": "customer", "text": "hola"}],
        turn_index=2,
        max_turns=5,
    )

    assert simulated["goal_reached"] is True
    assert simulated["message"] == ""


# ---------------------------------------------------------------------------
# Persisted facts — the judge may not contradict what the database recorded
# ---------------------------------------------------------------------------


def _flat(text):
    """The prompt is prose: assert the contract, not its line wrapping."""
    return " ".join(text.replace("`", "").split())


def _judge(monkeypatch, reply=None):
    reply = reply or (
        '{"dimensions": {'
        + ", ".join(f'"{n}": {{"score": 3, "evidence": "cita"}}' for n in judge.DIMENSIONS)
        + '}, "hard_fail": false}'
    )
    chat, calls = fake_chat([reply])
    monkeypatch.setattr(judge, "_chat", chat)
    return calls


def test_the_judge_receives_the_persisted_facts(monkeypatch):
    calls = _judge(monkeypatch)
    judge.judge_conversation(
        object(),
        transcript=[{"role": "customer", "text": "quiero hablar con una persona"}],
        scenario={"id": "x"},
        kb_text="",
        tarifario="",
        facts={
            "final_state": "human",
            "events": [
                {"event": "classified", "cause": "intent:postventa"},
                {"event": "escalation", "cause": "handoff:persona"},
            ],
        },
    )

    prompt = calls[0][1]["content"]
    assert "Persisted facts" in prompt
    assert "final state: `human`" in prompt
    assert "escalation (handoff:persona)" in prompt


def test_the_judge_is_told_a_recorded_hand_off_did_happen(monkeypatch):
    calls = _judge(monkeypatch)
    judge.judge_conversation(
        object(),
        transcript=[{"role": "customer", "text": "hola"}],
        scenario={"id": "x"},
        kb_text="",
        tarifario="",
        facts={"final_state": "human", "events": [{"event": "escalation", "cause": "handoff:persona"}]},
    )

    instructions = _flat(calls[0][0]["content"])
    assert "never claim the hand-off did not happen" in instructions


def test_a_run_without_facts_still_judges(monkeypatch):
    calls = _judge(monkeypatch)
    verdict = judge.judge_conversation(
        object(), transcript=[], scenario={"id": "x"}, kb_text="", tarifario=""
    )

    assert verdict["hard_fail"] is False
    assert "Persisted facts" not in calls[0][1]["content"]


def test_a_declared_hard_fail_must_be_reported_not_weighed(monkeypatch):
    calls = _judge(monkeypatch)
    judge.judge_conversation(
        object(),
        transcript=[{"role": "customer", "text": "hola"}],
        scenario={"id": "x", "hard_fails": ["Seguir vendiendo un servicio"]},
        kb_text="",
        tarifario="",
    )

    prompt = _flat(calls[0][0]["content"])
    assert "set hard_fail true" in prompt
    assert "caps the case at 0" in prompt


def test_the_policy_rubric_covers_a_complaint(monkeypatch):
    calls = _judge(monkeypatch)
    judge.judge_conversation(
        object(), transcript=[], scenario={"id": "x"}, kb_text="", tarifario=""
    )

    prompt = calls[0][1]["content"]
    assert "complaint" in prompt
    assert "already described" in prompt


def test_the_escalation_rubric_defers_to_the_facts(monkeypatch):
    calls = _judge(monkeypatch)
    judge.judge_conversation(
        object(), transcript=[], scenario={"id": "x"}, kb_text="", tarifario=""
    )

    assert "recorded" in calls[0][1]["content"]
