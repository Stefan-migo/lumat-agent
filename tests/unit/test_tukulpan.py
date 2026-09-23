import json
import logging

import pytest

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


def test_bounded_json_truncation_remains_valid_and_within_byte_bound():
    result = tukulpan._bounded_json({"preview": "á" * 100}, limit=40)

    assert len(result.encode("utf-8")) <= 40
    assert json.loads(result)["truncated"] is True
