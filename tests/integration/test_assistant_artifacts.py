from pathlib import Path

import pytest

from app.config import get_settings
from app.db import SessionLocal
from app.models import AssistantArtifact, InternalChatThread, User
from app.services.assistant_artifacts import get_artifact, list_artifacts, owned_thread, store_artifact
from app.services.users import hash_password


def test_store_artifact_round_trip_is_thread_scoped_and_private(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    with SessionLocal() as session:
        owner = User(username="artifact-service-owner", password_hash=hash_password("pass"), role="admin")
        other = User(username="artifact-service-other", password_hash=hash_password("pass"), role="admin")
        session.add_all([owner, other])
        session.flush()
        thread = InternalChatThread(user_id=owner.id)
        session.add(thread)
        session.flush()

        assert owned_thread(session, thread.id, owner.id) is not None
        assert owned_thread(session, thread.id, other.id) is None
        with pytest.raises(ValueError, match="empty"):
            store_artifact(session, thread, "empty.txt", "", "assistant")
        monkeypatch.setenv("ASSISTANT_ARTIFACT_MAX_BYTES", "2")
        get_settings.cache_clear()
        with pytest.raises(ValueError, match="size"):
            store_artifact(session, thread, "large.txt", "large", "assistant")
        monkeypatch.setenv("ASSISTANT_ARTIFACT_MAX_BYTES", str(5 * 1024 * 1024))
        get_settings.cache_clear()
        row = store_artifact(session, thread, "report.md", "abc", "assistant")
        session.flush()

        assert Path(row.stored_path).read_bytes() == b"abc"
        assert Path(row.stored_path).parent == tmp_path / "assistant_artifacts" / str(thread.id)
        assert [item.id for item in list_artifacts(session, thread.id)] == [row.id]
        assert get_artifact(session, thread.id, row.id).sha256 == row.sha256
        assert get_artifact(session, thread.id + 1, row.id) is None
        session.rollback()
    get_settings.cache_clear()


def test_artifact_download_and_thread_metadata_are_owner_scoped(client, monkeypatch, tmp_path):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    first, second = "artifact-api-owner", "artifact-api-other"
    with SessionLocal() as session:
        session.add_all([
            User(username=first, password_hash=hash_password("pass"), role="admin"),
            User(username=second, password_hash=hash_password("pass"), role="admin"),
        ])
        session.commit()

    assert client.post("/panel/api/login", json={"username": first, "password": "pass"}).status_code == 200
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        artifact = store_artifact(session, thread, "report.md", "artifact bytes", first)
        session.commit()
        artifact_id = artifact.id

    path = f"/panel/api/chat/threads/{thread_id}/artifacts/{artifact_id}/download"
    downloaded = client.get(path)
    assert downloaded.status_code == 200
    assert downloaded.content == b"artifact bytes"
    metadata = client.get(f"/panel/api/chat/threads/{thread_id}").json()["artifacts"][0]
    assert metadata["filename"] == "report.md"
    assert "stored_path" not in metadata

    client.post("/panel/api/logout")
    assert client.post("/panel/api/login", json={"username": second, "password": "pass"}).status_code == 200
    assert client.get(path).status_code == 404
    get_settings.cache_clear()
