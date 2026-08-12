"""T0.2 — app factory + environment config.

Mirrors the T0.2 runtime acceptance as focused tests:
- `/health` returns 200 with status ok + version
- a missing required env var produces a clear boot-time error
"""

import pytest

from app.config import get_settings


def test_health_returns_ok_and_version(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"


def test_missing_required_env_raises_clear_boot_error(monkeypatch):
    monkeypatch.delenv("APP_SECRET", raising=False)
    get_settings.cache_clear()
    with pytest.raises(Exception, match="app_secret"):
        get_settings()
    get_settings.cache_clear()
