"""Shared fixtures for the integration suite (T0.2; extended by T1.2/T6.1).

Sets the full required environment BEFORE any `app.*` import so that
`app.main`'s module-level `create_app()` succeeds at collection time.

Batch 1 additions:
- DATABASE_URL now points at the real test DB (`lumat`, app role) — Batch 0
  never connected, so this is a no-op for B0 tests.
- `run_migrate()` / `migrated_db` fixture: apply schema via db/migrate.sh
  (idempotent) so integration tests run against the migrated schema.

Batch 3 additions:
- `mock_openai_chat` / `mock_openai_embeddings`: deterministic respx mocks
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

REPO_ROOT = Path(__file__).resolve().parents[2]

TEST_ENV = {
    "APP_SECRET": "test-app-secret",
    "VERIFY_TOKEN": "test-verify-token",
    "DATABASE_URL": "postgresql+psycopg://app:app@localhost:5432/lumat",
    "OPENAI_API_KEY": "sk-test",
    "META_ACCESS_TOKEN": "meta-test-token",
    "META_PHONE_NUMBER_ID": "123456789",
    # LangGraph auto-tracing (langsmith) must never hit the network in tests.
    "LANGCHAIN_TRACING_V2": "false",
    "LANGCHAIN_TRACING": "false",
}

for _key, _value in TEST_ENV.items():
    os.environ.setdefault(_key, _value)

# The dev shell may carry a real OPENAI_API_KEY — tests MUST mock OpenAI via
# respx and must NEVER use that key. Force the test key so an accidentally
# unmocked call fails fast (401) instead of spending real tokens/hanging.
os.environ["OPENAI_API_KEY"] = "sk-test"

from app.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402

ADMIN_DB_URL = os.environ.get(
    "TEST_ADMIN_DB_URL", "postgresql://lumat:lumat@localhost:5432/lumat"
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


@pytest.fixture
def client() -> TestClient:
    """A TestClient over a freshly built app with the test environment."""
    get_settings.cache_clear()
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# Batch 3 — OpenAI mocks (respx; deterministic, never a real call)
# ---------------------------------------------------------------------------

EMBED_DIMS = 1536


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
    """Mock OpenAI /chat/completions; captures requests.

    Dispatches by prompt role: summary prompt -> canned summary; respond
    prompt (has <kb>) -> grounded answer; otherwise -> intent classification.
    """
    captured: list[dict] = []

    with respx.mock(base_url="https://api.openai.com/v1", assert_all_called=False) as router:

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
                    "model": "gpt-4o-mini",
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
def mock_openai_embeddings():
    """Mock OpenAI /embeddings with deterministic one-hot vectors."""
    with respx.mock(base_url="https://api.openai.com/v1", assert_all_called=False) as router:

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            inputs = body["input"]
            if isinstance(inputs, str):
                inputs = [inputs]
            data = [
                {"object": "embedding", "index": i, "embedding": fake_embedding(t)}
                for i, t in enumerate(inputs)
            ]
            tokens = max(1, sum(len(i) // 4 for i in inputs))
            return httpx.Response(
                200,
                json={
                    "object": "list",
                    "model": "text-embedding-3-small",
                    "data": data,
                    "usage": {"prompt_tokens": tokens, "total_tokens": tokens},
                },
            )

        router.post("/embeddings").mock(side_effect=handler)
        yield router
