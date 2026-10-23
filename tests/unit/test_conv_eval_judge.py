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
