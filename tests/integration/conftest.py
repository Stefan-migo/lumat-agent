"""Shared fixtures for the integration suite (T0.2; extended by T1.2/T6.1).

Sets the full required environment BEFORE any `app.*` import so that
`app.main`'s module-level `create_app()` succeeds at collection time.

Batch 1 additions:
- DATABASE_URL now points at the real test DB (`lumat`, app role) — Batch 0
  never connected, so this is a no-op for B0 tests.
- `run_migrate()` / `migrated_db` fixture: apply schema via db/migrate.sh
  (idempotent) so integration tests run against the migrated schema.

Batch 3 additions:
- `mock_openai_chat` / `fake_embedder`: respx + monkeypatch mocks — chat
  completions (deepseek default provider) and the local embedder (no download)
  for the OpenAI API (never a real call — the dev shell key is NOT used).
"""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from _testdb import admin_database_url, database_url

REPO_ROOT = Path(__file__).resolve().parents[2]

TEST_ENV = {
    "APP_SECRET": "test-app-secret",
    "VERIFY_TOKEN": "test-verify-token",
    "DATABASE_URL": database_url(),
    "DEEPSEEK_API_KEY": "sk-test",
    "META_ACCESS_TOKEN": "meta-test-token",
    "META_PHONE_NUMBER_ID": "123456789",
    # T5.1: panel session cookie signing secret (AP-1) — required at boot.
    "PANEL_SESSION_SECRET": "test-panel-session-secret",
    # LangGraph auto-tracing (langsmith) must never hit the network in tests.
    "LANGCHAIN_TRACING_V2": "false",
    "LANGCHAIN_TRACING": "false",
}

for _key, _value in TEST_ENV.items():
    os.environ.setdefault(_key, _value)

# The dev shell may carry a real DEEPSEEK_API_KEY — tests MUST mock chat via
# respx and must NEVER use that key. Force the test key so an accidentally
# unmocked call fails fast (401) instead of spending real tokens/hanging.
os.environ["DEEPSEEK_API_KEY"] = "sk-test"

from app.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402

ADMIN_DB_URL = admin_database_url()


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


@pytest.fixture
def client() -> TestClient:
    """A TestClient over a freshly built app with the test environment."""
    get_settings.cache_clear()
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# Batch 3 — OpenAI mocks (respx; deterministic, never a real call)
# ---------------------------------------------------------------------------

EMBED_DIMS = 384


def fake_embedding(text: str) -> list[float]:
    """Deterministic bag-of-char-trigrams hashed into buckets.

    Related texts share trigrams (e.g. "cuanto cuesta la revision anual" is a
    prefix of a chunk with the same words) so cosine similarity is meaningful:
    near-identical -> >0.8, unrelated -> ~0. Identical text -> 1.0.
    """
    vec = [0.0] * EMBED_DIMS
    lowered = text.lower()
    for i in range(len(lowered) - 2):
        bucket = (
            int.from_bytes(hashlib.sha256(lowered[i : i + 3].encode()).digest()[:4], "big")
            % EMBED_DIMS
        )
        vec[bucket] = 1.0
    if not any(vec):
        vec[0] = 1.0  # degenerate (empty/tiny) input
    return vec


def classify_result_for(text: str) -> dict:
    """Deterministic intent classification mirroring the LLM contract."""
    tl = text.lower()
    injection = (
        "ignora tus instrucciones" in tl
        or "revela" in tl
        or "manipula el sistema" in tl
        or "panel interno" in tl
        or "actua como" in tl
    )
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
    """Mock chat completions (deepseek default provider); captures requests.

    Dispatches by prompt role: summary prompt -> canned summary; respond
    prompt (has <kb>) -> grounded answer; otherwise -> intent classification.
    (The embedder is autouse-mounted via `fake_embedder`.)
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


@pytest.fixture(autouse=True)
def fake_embedder(monkeypatch):
    """Swap kb.get_embedder() for a deterministic fake (no model download).

    Autouse: S2 runs the graph through run_conversation/process_message on
    every turn, which persists per-turn memory (an embedding). The project
    contract is that the suite NEVER downloads the ~130MB model, so the seam is
    mounted by default for every integration test. Tests asserting on the
    embedder itself define their own fake (test_kb.py) that shadows this one.
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
