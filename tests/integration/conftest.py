"""Shared fixtures for the integration suite (T0.2; extended by T6.1).

Sets the full required environment BEFORE any `app.*` import so that
`app.main`'s module-level `create_app()` succeeds at collection time.
"""

import os

import pytest
from fastapi.testclient import TestClient

TEST_ENV = {
    "APP_SECRET": "test-app-secret",
    "VERIFY_TOKEN": "test-verify-token",
    "DATABASE_URL": "postgresql://app:app@localhost:5432/app",
    "OPENAI_API_KEY": "sk-test",
    "META_ACCESS_TOKEN": "meta-test-token",
    "META_PHONE_NUMBER_ID": "123456789",
}

for _key, _value in TEST_ENV.items():
    os.environ.setdefault(_key, _value)

from app.config import get_settings  # noqa: E402  (env must be set first)
from app.main import create_app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    """A TestClient over a freshly built app with the test environment."""
    get_settings.cache_clear()
    return TestClient(create_app())
