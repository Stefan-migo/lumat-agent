"""The dev-settings contract both repo-root scripts rely on.

`app.config.Settings` is fail-fast: five webhook/panel values are required even
though neither `seed_kb_docs.py` nor `conv_eval.py` touches the webhook or the
panel. `ensure_dev_env` fills only what is missing, so a documented command runs
from the repo root while a real environment always wins.
"""

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import seed_kb_docs  # noqa: E402

DEV_SETTINGS = (
    "APP_SECRET",
    "VERIFY_TOKEN",
    "META_ACCESS_TOKEN",
    "META_PHONE_NUMBER_ID",
    "PANEL_SESSION_SECRET",
)


def reload_seed(monkeypatch):
    monkeypatch.setattr(seed_kb_docs, "_DEV_ONLY_SETTINGS", DEV_SETTINGS)
    return importlib.reload(seed_kb_docs)


def test_missing_settings_are_filled_with_placeholders(monkeypatch):
    import os

    for name in DEV_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    reload_seed(monkeypatch)
    for name in DEV_SETTINGS:
        assert os.environ[name] == f"conv-eval-{name.lower()}"


def test_a_real_value_is_never_overwritten(monkeypatch):
    import os

    for name in DEV_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("APP_SECRET", "un-secreto-real")
    reload_seed(monkeypatch)
    assert os.environ["APP_SECRET"] == "un-secreto-real"
    assert os.environ["VERIFY_TOKEN"] == "conv-eval-verify_token"


def test_the_helper_is_idempotent(monkeypatch):
    import os

    for name in DEV_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    reload_seed(monkeypatch)
    before = {name: os.environ[name] for name in DEV_SETTINGS}
    reload_seed(monkeypatch)
    assert {name: os.environ[name] for name in DEV_SETTINGS} == before


def test_no_credential_is_ever_invented(monkeypatch):
    import os

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    reload_seed(monkeypatch)
    assert "DEEPSEEK_API_KEY" not in os.environ
