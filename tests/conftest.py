"""Batch 6 shared test harness (T6.1) — fixtures for the injection + functional suites.

This is the TOP-LEVEL tests conftest. The suite conftests
(tests/integration/conftest.py, tests/functional/conftest.py) shadow these
fixtures for their own directories — existing tests behave EXACTLY as before.
The Batch 6 suites that have no local conftest of their own
(tests/injection/) and the new functional webhook flows use the shared copies
defined here:

- full test environment set before ANY `app.*` import (same pattern as the
  suite conftests; the dev-shell real DEEPSEEK_API_KEY is forced to sk-test so
  an accidentally unmocked call fails fast instead of spending tokens)
- `migrated_db` / `clean_db`: migrations once per session, full table reset
  per test (shared test DB — compose `test` profile, see infra/docker-compose.yml)
- `client`: TestClient over a freshly built app
- `seed_customer`: get-or-create a ficha (CR-1/CR-2 fixtures)
- `mock_openai_chat` / `fake_embedder` / `mock_meta_send`: respx + monkeypatch
  mocks — chat completions (deepseek default provider) are NEVER called for
  real; the local fastembed embedder is swapped for a deterministic fake
  (no model download); Meta sends are intercepted
- `_reset_rate_limiter` (autouse): the in-memory webhook rate limiter is
  module state; without a per-test reset, messages accumulate across tests
  from the same phone and get dropped after 15/min.
"""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import httpx
import psycopg
import pytest
import respx
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]

TEST_ENV = {
    "APP_SECRET": "test-app-secret",
    "VERIFY_TOKEN": "test-verify-token",
    "DATABASE_URL": "postgresql+psycopg://app:app@localhost:5432/lumat",
    "DEEPSEEK_API_KEY": "sk-test",
    "META_ACCESS_TOKEN": "meta-test-token",
    "META_PHONE_NUMBER_ID": "123456789",
    "PANEL_SESSION_SECRET": "test-panel-session-secret",
    # LangGraph auto-tracing (langsmith) must never hit the network in tests.
    "LANGCHAIN_TRACING_V2": "false",
    "LANGCHAIN_TRACING": "false",
}

for _key, _value in TEST_ENV.items():
    os.environ.setdefault(_key, _value)

# Force the test key — the dev shell may export a REAL DEEPSEEK_API_KEY.
os.environ["DEEPSEEK_API_KEY"] = "sk-test"

from app.chat.nodes.classify_intent import is_injection  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402

ADMIN_DB_URL = os.environ.get(
    "TEST_ADMIN_DB_URL", "postgresql://lumat:lumat@localhost:5432/lumat"
)

# Tables truncated before each test (full set — shared test DB).
TRUNCATE_TABLES = (
    "notification_attempts, notification_operations, appointment_history, appointments, technician_availability, settings, audit_log, kb_chunks, kb_documents, conversation_events, "
    "automation_rules, automation_executions, domain_events, "
    "cases, internal_chat_messages, internal_chat_threads, messages, conversations, customer_notes, users, customers"
)


def run_migrate() -> subprocess.CompletedProcess:
    """Run db/migrate.sh against the test DB (idempotent)."""
    env = os.environ.copy()
    env["DATABASE_URL"] = ADMIN_DB_URL
    env["APP_DB_PASSWORD"] = "app"
    env["PYTHON"] = str(REPO_ROOT / ".venv" / "bin" / "python")
    return subprocess.run(
        ["bash", str(REPO_ROOT / "db" / "migrate.sh")],
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="session")
def migrated_db() -> None:
    """Apply migrations once per session (idempotent runner)."""
    result = run_migrate()
    assert result.returncode == 0, (
        f"migrate.sh failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )


@pytest.fixture(autouse=True)
def clean_db(migrated_db) -> None:
    """Reset all tables before every test (shared test DB)."""
    with psycopg.connect(ADMIN_DB_URL, autocommit=True) as conn:
        conn.execute(f"TRUNCATE {TRUNCATE_TABLES} RESTART IDENTITY CASCADE")
    yield


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The in-memory webhook rate limiter is module state; reset per test."""
    from app.webhook import ingest

    ingest.rate_limiter.reset()
    yield


@pytest.fixture
def client() -> TestClient:
    """A TestClient over a freshly built app with the test environment."""
    get_settings.cache_clear()
    return TestClient(create_app())


@pytest.fixture
def seed_customer():
    """Get-or-create a ficha by phone (CR-1/CR-2 seeding helper)."""

    def _seed(phone: str):
        from app.db import SessionLocal
        from app.services.customers import get_or_create_customer

        with SessionLocal() as session:
            customer = get_or_create_customer(session, phone)
            session.commit()
            return customer.id

    return _seed


# ---------------------------------------------------------------------------
# OpenAI + Meta mocks (respx; deterministic, never a real call)
# ---------------------------------------------------------------------------

EMBED_DIMS = 384

# LLM-flag phrases for the injection suite: payloads the production
# deterministic pattern set does NOT match but that are clearly manipulation
# attempts. The mock flags them so the classify call reports injection=true
# (SH-4 "Injection attempt treated as data" — the LLM is the second layer).
_LLM_INJECTION_PHRASES = (
    "panel interno",
    "token de la api",
    "secretos",
    "manipula",
    "dame acceso",
    "haz caso omiso",
    "ignora todo lo anterior",
    "cuentame",
)


def fake_embedding(text: str) -> list[float]:
    """Deterministic bag-of-char-trigrams hashed into buckets."""
    vec = [0.0] * EMBED_DIMS
    lowered = text.lower()
    for i in range(len(lowered) - 2):
        bucket = (
            int.from_bytes(hashlib.sha256(lowered[i : i + 3].encode()).digest()[:4], "big")
            % EMBED_DIMS
        )
        vec[bucket] = 1.0
    if not any(vec):
        vec[0] = 1.0
    return vec


def classify_result_for(text: str) -> dict:
    """Deterministic intent classification mirroring the LLM contract.

    Injection detection = production deterministic patterns (imported from
    classify_intent) OR the LLM-flag phrase list above — mirroring the two
    SH-4 layers (deterministic gate first, LLM flag second).
    """
    tl = text.lower()
    injection = is_injection(tl) or any(p in tl for p in _LLM_INJECTION_PHRASES)
    if "caldera" in tl:
        return {"intent": "caldera", "service": "caldera", "priority": "media", "status": "abierto", "injection": injection}
    if "calefont" in tl:
        return {"intent": "calefont", "service": "calefont", "priority": "media", "status": "abierto", "injection": injection}
    if "calefaccion" in tl:
        return {"intent": "calefaccion", "service": "calefaccion", "priority": "media", "status": "abierto", "injection": injection}
    if "visita" in tl:
        return {"intent": "solicitar_visita", "service": "visita", "priority": "alta", "status": "abierto", "injection": injection}
    if "precio" in tl or "valor" in tl or "cuesta" in tl or "cuanto" in tl:
        return {"intent": "valores", "service": "valores", "priority": "baja", "status": None, "injection": injection}
    if "persona" in tl:
        return {"intent": "persona", "service": None, "priority": None, "status": None, "injection": injection}
    if "emergencia" in tl or "incendio" in tl:
        return {"intent": "emergencia", "service": None, "priority": "alta", "status": "escalado", "injection": injection}
    return {"intent": "unknown", "service": None, "priority": None, "status": None, "injection": injection}


@pytest.fixture
def mock_openai_chat():
    """Mock the chat-completions endpoint (deepseek default provider).

    Dispatches by prompt role: summary prompt -> canned summary; respond
    prompt (has <kb>) -> grounded answer; otherwise -> intent classification
    (with the SH-4 injection flag set by classify_result_for).
    """
    captured: list[dict] = []

    with respx.mock(base_url="https://api.deepseek.com", assert_all_called=False) as router:

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            captured.append(body)
            system = body["messages"][0]["content"]
            user = body["messages"][-1]["content"]
            if "resumen" in system.lower():
                content = (
                    "Resumen de prueba: cliente con calefont en Providencia, "
                    "se solicita visita tecnica."
                )
            elif "<kb>" in user:
                kb_text = user.split("<kb>")[1].split("</kb>")[0]
                content = f"Segun el manual de Lumat: {kb_text[:120]}..."
            else:
                inner = (
                    user.split("<user_input>")[1].split("</user_input>")[0]
                    if "<user_input>" in user
                    else ""
                )
                content = json.dumps(classify_result_for(inner), ensure_ascii=False)
            return httpx.Response(
                200,
                json={
                    "id": "cmpl-test",
                    "object": "chat.completion",
                    "created": 0,
                    "model": "deepseek-chat",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": content},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
                },
            )

        router.post("/chat/completions").mock(side_effect=handler)
        yield captured


@pytest.fixture
def fake_embedder(monkeypatch):
    """Swap kb.get_embedder() for a deterministic fake (no model download).

    The fake mirrors the fastembed seam (`.embed(texts)` -> iterable of
    vectors), returning one-hot trigram-bucket vectors of kb.EMBED_DIMS, so
    KB retrieval behaves deterministically in tests.
    """
    from app.services import kb as kb_service

    class _FakeEmbedder:
        def embed(self, texts):
            return (fake_embedding(t) for t in texts)

    monkeypatch.setattr(kb_service, "get_embedder", lambda: _FakeEmbedder())


@pytest.fixture
def mock_meta_send():
    """Intercept the Meta Cloud API outbound text send."""
    with respx.mock(base_url="https://graph.facebook.com") as router:
        router.post("/v20.0/123456789/messages").mock(
            return_value=httpx.Response(
                200,
                json={"messaging_product": "whatsapp", "messages": [{"id": "wamid.out123"}]},
            )
        )
        yield router
