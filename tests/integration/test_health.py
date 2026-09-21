"""T0.2 — app factory + environment config.

Mirrors the T0.2 runtime acceptance as focused tests:
- `/health` returns 200 with status ok + version
- a missing required env var produces a clear boot-time error
"""

import pytest
import tomllib
from fastapi.testclient import TestClient

import app.config as config
from app.config import get_settings
from app.main import create_app


def test_health_returns_ok_and_version(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    with config.PYPROJECT_PATH.open("rb") as pyproject:
        expected_version = tomllib.load(pyproject)["project"]["version"]
    assert body["version"] == expected_version
    assert "commit" in body


def test_health_uses_redirected_version_source_and_git_sha(monkeypatch, tmp_path):
    version_source = tmp_path / "pyproject.toml"
    version_source.write_text('[project]\nversion = "2099.12.1"\n')
    monkeypatch.setattr(config, "PYPROJECT_PATH", version_source)
    monkeypatch.setenv("GIT_SHA", "abc1234")
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as fresh_client:
            body = fresh_client.get("/health").json()
        assert body["version"] == "2099.12.1"
        assert body["commit"] == "abc1234"
    finally:
        get_settings.cache_clear()


def test_missing_required_env_raises_clear_boot_error(monkeypatch):
    monkeypatch.delenv("APP_SECRET", raising=False)
    get_settings.cache_clear()
    with pytest.raises(Exception, match="app_secret"):
        get_settings()
    get_settings.cache_clear()
