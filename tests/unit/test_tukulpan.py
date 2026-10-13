import logging

import pytest

from app.db import SessionLocal
from app.models import MemoryType, MemoryVisibility
from app.services import tukulpan


def test_embed_retries_with_declared_backoff_and_logs_final_failure(monkeypatch, caplog):
    calls = []
    sleeps = []

    def fail_embedding(texts):
        calls.append(texts)
        raise RuntimeError("embedder unavailable")

    monkeypatch.setattr(tukulpan.kb, "embed_texts", fail_embedding)
    monkeypatch.setattr(tukulpan.time, "sleep", sleeps.append)

    with caplog.at_level(logging.ERROR, logger=tukulpan.logger.name):
        with pytest.raises(RuntimeError, match="embedder unavailable"):
            tukulpan._embed(["memory text"])

    assert len(calls) == tukulpan.EMBED_RETRIES + 1
    assert sleeps == list(tukulpan.EMBED_BACKOFF_SECONDS)
    assert any("memory embedding failed after 3 attempts" in record.message for record in caplog.records)


def test_upsert_preserves_handoff_when_omitted_and_clears_when_explicit(monkeypatch):
    monkeypatch.setattr(tukulpan, "_embed", lambda _texts: [[0.0] * 384])
    with SessionLocal() as session:
        kwargs = {
            "scope": "agent",
            "entity_id": "agent:handoff-upsert-test",
            "topic_key": "agent:handoff-upsert-test",
            "tipo": MemoryType.DECISION,
            "titulo": "Handoff marker",
            "contenido": "Pending continuation",
            "visibility": MemoryVisibility.GLOBAL,
        }
        first = tukulpan.upsert(session, **kwargs, handoff=True)
        assert first.handoff is True

        repeated = tukulpan.upsert(session, **kwargs)
        assert repeated.handoff is True

        cleared = tukulpan.upsert(session, **kwargs, handoff=False)
        assert cleared.handoff is False
