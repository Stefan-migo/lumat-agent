import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import AssistantArtifact, AuditLog, InternalChatThread, User
from app.services.assistant_artifacts import (
    append_revision,
    delete_artifact,
    get_artifact,
    get_current,
    get_revision,
    list_artifacts,
    owned_thread,
    revision_chain,
    store_artifact,
)
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


def _artifact_fixture(session, monkeypatch, tmp_path, username: str, content: str = "abc"):
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    owner = User(username=username, password_hash=hash_password("pass"), role="admin")
    session.add(owner)
    session.flush()
    thread = InternalChatThread(user_id=owner.id)
    session.add(thread)
    session.flush()
    return owner, thread, store_artifact(session, thread, "report.md", content, "assistant")


def test_editing_an_artifact_appends_a_revision_and_keeps_every_blob(monkeypatch, tmp_path):
    """S1/S9: an edit is a new row with the next version; the old blob is never touched."""
    with SessionLocal() as session:
        owner, thread, first = _artifact_fixture(session, monkeypatch, tmp_path, "artifact-edit-owner")
        assert (first.root_id, first.version) == (first.id, 1)
        first_digest, first_path = first.sha256, first.stored_path

        second, changed = append_revision(session, thread, first, "abcd", actor="assistant")
        session.flush()

        assert changed is True
        assert second.id != first.id
        assert (second.root_id, second.version) == (first.root_id, 2)
        assert (second.filename, second.content_type) == ("report.md", "text/markdown")
        assert Path(second.stored_path) != Path(first_path)
        assert Path(second.stored_path).read_bytes() == b"abcd"
        assert Path(first_path).read_bytes() == b"abc"
        assert get_artifact(session, thread.id, first.id).sha256 == first_digest

        # S2: the thread lists the current version only, once per artifact.
        assert [item.id for item in list_artifacts(session, thread.id)] == [second.id]
        assert revision_chain(session, thread.id)[first.root_id] == [first, second]
        assert get_current(session, thread.id, first.id).id == second.id
        assert get_current(session, thread.id, second.id).id == second.id
        assert get_revision(session, thread.id, first.id, 1).id == first.id

        audit = session.execute(
            select(AuditLog).where(AuditLog.action == "assistant_artifact.updated")
        ).scalar_one()
        assert audit.entity_id == str(second.id)
        assert audit.after["previous_version"] == 1
        assert audit.after["version"] == 2
        assert audit.after["root_id"] == first.root_id
        session.rollback()
    get_settings.cache_clear()


def test_repeating_the_same_content_appends_no_revision(monkeypatch, tmp_path):
    """S7: identical bytes are not a new version — no row, no blob, no audit."""
    with SessionLocal() as session:
        _owner, thread, first = _artifact_fixture(session, monkeypatch, tmp_path, "artifact-same-owner")
        blobs_before = sorted(p.name for p in (tmp_path / "assistant_artifacts" / str(thread.id)).iterdir())

        repeated, changed = append_revision(session, thread, first, "abc", actor="assistant")
        session.flush()

        assert changed is False
        assert repeated.id == first.id
        assert [item.id for item in list_artifacts(session, thread.id)] == [first.id]
        assert sorted(p.name for p in (tmp_path / "assistant_artifacts" / str(thread.id)).iterdir()) == blobs_before
        assert session.execute(select(AuditLog).where(AuditLog.action == "assistant_artifact.updated")).first() is None
        session.rollback()
    get_settings.cache_clear()


def test_editing_rejects_empty_or_oversized_content_and_changes_nothing(monkeypatch, tmp_path):
    """S8: the limits of store_artifact apply to an edit, and a rejection mutates nothing."""
    with SessionLocal() as session:
        _owner, thread, first = _artifact_fixture(session, monkeypatch, tmp_path, "artifact-limit-owner")
        rows_before = session.execute(select(AssistantArtifact).where(AssistantArtifact.thread_id == thread.id)).scalars().all()

        with pytest.raises(ValueError, match="empty"):
            append_revision(session, thread, first, "", actor="assistant")
        monkeypatch.setenv("ASSISTANT_ARTIFACT_MAX_BYTES", "2")
        get_settings.cache_clear()
        with pytest.raises(ValueError, match="size"):
            append_revision(session, thread, first, "abcd", actor="assistant")
        monkeypatch.setenv("ASSISTANT_ARTIFACT_MAX_BYTES", str(5 * 1024 * 1024))
        get_settings.cache_clear()

        rows_after = session.execute(select(AssistantArtifact).where(AssistantArtifact.thread_id == thread.id)).scalars().all()
        assert [row.id for row in rows_after] == [row.id for row in rows_before]
        assert len(list((tmp_path / "assistant_artifacts" / str(thread.id)).iterdir())) == 1
        session.rollback()
    get_settings.cache_clear()


def test_concurrent_edits_get_distinct_versions(monkeypatch, tmp_path):
    """S11: two simultaneous edits of one artifact cannot claim the same version."""
    with SessionLocal() as session:
        _owner, thread, first = _artifact_fixture(session, monkeypatch, tmp_path, "artifact-race-owner")
        session.commit()
        thread_id, artifact_id, root_id = thread.id, first.id, first.root_id

    ready = threading.Barrier(2)
    versions: list[int] = []
    errors: list[BaseException] = []

    def edit(content: str) -> None:
        try:
            with SessionLocal() as session:
                thread = session.get(InternalChatThread, thread_id)
                artifact = get_artifact(session, thread_id, artifact_id)
                ready.wait(timeout=30)
                row, _changed = append_revision(session, thread, artifact, content, actor="assistant")
                session.commit()
                versions.append(row.version)
        except BaseException as exc:  # noqa: BLE001 - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=edit, args=(content,)) for content in ("race-a", "race-b")]
    for worker in threads:
        worker.start()
    for worker in threads:
        worker.join(timeout=60)

    assert errors == []
    assert sorted(versions) == [2, 3]
    with SessionLocal() as session:
        rows = session.execute(
            select(AssistantArtifact).where(AssistantArtifact.root_id == root_id)
        ).scalars().all()
        assert sorted(row.version for row in rows) == [1, 2, 3]
        assert [row.id for row in list_artifacts(session, thread_id)] == [
            max(rows, key=lambda row: row.version).id
        ]
    get_settings.cache_clear()


def test_download_serves_the_current_version_and_any_named_one(client, monkeypatch, tmp_path):
    """S3/S4: a path written before an edit keeps working and shows the current content."""
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    username = "artifact-version-api"
    with SessionLocal() as session:
        session.add(User(username=username, password_hash=hash_password("pass"), role="admin"))
        session.commit()

    assert client.post("/panel/api/login", json={"username": username, "password": "pass"}).status_code == 200
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        first = store_artifact(session, thread, "report.md", "version one", username)
        second, _changed = append_revision(session, thread, first, "version two", actor="assistant")
        session.commit()
        first_id, second_id, root_id = first.id, second.id, first.root_id

    # The path a message wrote at version 1 still serves the current content.
    current = client.get(f"/panel/api/chat/threads/{thread_id}/artifacts/{first_id}/download")
    assert current.status_code == 200
    assert current.content == b"version two"
    named = client.get(f"/panel/api/chat/threads/{thread_id}/artifacts/{first_id}/download?version=1")
    assert named.status_code == 200
    assert named.content == b"version one"
    latest_named = client.get(f"/panel/api/chat/threads/{thread_id}/artifacts/{second_id}/download?version=2")
    assert latest_named.status_code == 200
    assert latest_named.content == b"version two"
    missing = client.get(f"/panel/api/chat/threads/{thread_id}/artifacts/{first_id}/download?version=9")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "artifact version not found"
    unknown = client.get(f"/panel/api/chat/threads/{thread_id}/artifacts/999999/download")
    assert unknown.status_code == 404
    assert unknown.json()["detail"] == "artifact not found"

    # S2/S10: the thread lists the current version once, with its revision history.
    artifacts = client.get(f"/panel/api/chat/threads/{thread_id}").json()["artifacts"]
    assert [row["id"] for row in artifacts] == [second_id]
    assert artifacts[0]["root_id"] == root_id
    assert artifacts[0]["version"] == 2
    assert artifacts[0]["filename"] == "report.md"
    assert artifacts[0]["size"] == len(b"version two")
    assert [(item["version"], item["id"]) for item in artifacts[0]["versions"]] == [(1, first_id), (2, second_id)]
    assert "stored_path" not in artifacts[0]
    assert "sha256" not in artifacts[0]
    assert client.get(f"/panel/api/chat/threads/{thread_id}").json()["artifacts"][0]["versions"][0]["size"] == len(b"version one")
    get_settings.cache_clear()


def test_a_failed_insert_leaves_no_artifact_row_and_no_orphan_blob(monkeypatch, tmp_path):
    """R3-001: an insert that fails must not leave a blob on disk with no row behind it."""
    with SessionLocal() as session:
        owner, thread, first = _artifact_fixture(session, monkeypatch, tmp_path, "artifact-orphan-owner")
        session.commit()
        thread_id = thread.id

    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)

        def failing_flush(*_args, **_kwargs):
            raise RuntimeError("insert failed")

        monkeypatch.setattr(session, "flush", failing_flush)
        with pytest.raises(RuntimeError):
            store_artifact(session, thread, "informe.md", "second file", "assistant")
        session.rollback()

    with SessionLocal() as session:
        rows = session.execute(
            select(AssistantArtifact).where(AssistantArtifact.thread_id == thread_id)
        ).scalars().all()
        assert len(rows) == 1
        assert sorted(p.name for p in (tmp_path / "assistant_artifacts" / str(thread_id)).iterdir()) == [
            Path(first.stored_path).name
        ]
    get_settings.cache_clear()


def test_a_failed_identity_leaves_no_blob_on_disk(monkeypatch, tmp_path):
    """R3-001: a failure before the row exists never touches the media directory."""
    with SessionLocal() as session:
        owner, thread, _first = _artifact_fixture(session, monkeypatch, tmp_path, "artifact-identity-owner")
        session.commit()
        thread_id = thread.id
        files_before = sorted(p.name for p in (tmp_path / "assistant_artifacts" / str(thread_id)).iterdir())

        def failing_nextval(*_args, **_kwargs):
            raise RuntimeError("sequence unavailable")

        monkeypatch.setattr(
            "app.services.assistant_artifacts.text", lambda *_args, **_kwargs: SimpleNamespace()
        )
        monkeypatch.setattr(session, "execute", failing_nextval)
        with pytest.raises(RuntimeError):
            store_artifact(session, thread, "informe.md", "never lands", "assistant")
        session.rollback()

    assert sorted(p.name for p in (tmp_path / "assistant_artifacts" / str(thread_id)).iterdir()) == files_before
    get_settings.cache_clear()


def test_delete_artifact_removes_every_version_and_its_blobs(monkeypatch, tmp_path):
    """S3/S4: deleting an artifact removes all of its revisions, rows and blobs alike."""
    with SessionLocal() as session:
        owner, thread, first = _artifact_fixture(session, monkeypatch, tmp_path, "artifact-delete-owner")
        second, _changed = append_revision(session, thread, first, "second", actor="assistant")
        session.flush()
        root_id = first.root_id
        blobs = sorted(p.name for p in (tmp_path / "assistant_artifacts" / str(thread.id)).iterdir())
        assert len(blobs) == 2

        summary = delete_artifact(session, thread.id, first.id)
        session.commit()

        assert summary == {
            "artifact_id": first.id,
            "root_id": root_id,
            "filename": "report.md",
            "versions_deleted": 2,
            "deleted": True,
        }
        assert list_artifacts(session, thread.id) == []
        assert revision_chain(session, thread.id) == {}
        assert [p.name for p in (tmp_path / "assistant_artifacts" / str(thread.id)).iterdir()] == []
        assert get_artifact(session, thread.id, second.id) is None

        audit = session.execute(
            select(AuditLog).where(AuditLog.action == "assistant_artifact.deleted")
        ).scalar_one()
        assert audit.entity_id == str(first.id)
        assert audit.after["root_id"] == root_id
        assert audit.after["versions_deleted"] == 2
    get_settings.cache_clear()


def test_delete_artifact_endpoint_is_owner_scoped_and_removes_the_artifact(client, monkeypatch, tmp_path):
    """S3: the panel can hard-delete an artifact, and the download then 404s."""
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    username = "artifact-delete-api"
    with SessionLocal() as session:
        session.add(User(username=username, password_hash=hash_password("pass"), role="admin"))
        session.commit()

    assert client.post("/panel/api/login", json={"username": username, "password": "pass"}).status_code == 200
    thread_id = client.post("/panel/api/chat/threads", json={"proyecto": "default"}).json()["thread"]["id"]
    with SessionLocal() as session:
        thread = session.get(InternalChatThread, thread_id)
        first = store_artifact(session, thread, "report.md", "one", username)
        second, _changed = append_revision(session, thread, first, "two", actor="assistant")
        session.commit()
        first_id = first.id

    deleted = client.delete(f"/panel/api/chat/threads/{thread_id}/artifacts/{first_id}")
    assert deleted.status_code == 200
    assert deleted.json()["versions_deleted"] == 2
    assert deleted.json()["deleted"] is True
    assert client.get(f"/panel/api/chat/threads/{thread_id}/artifacts/{first_id}/download").status_code == 404
    assert client.get(f"/panel/api/chat/threads/{thread_id}").json()["artifacts"] == []

    # A foreign artifact id is not found.
    missing = client.delete(f"/panel/api/chat/threads/{thread_id}/artifacts/999999")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "artifact not found"
    get_settings.cache_clear()


def test_delete_artifact_keeps_blobs_when_the_transaction_rolls_back(monkeypatch, tmp_path):
    """R3-001: a rollback keeps the rows, so the files must survive it too."""
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    with SessionLocal() as session:
        owner, thread, first = _artifact_fixture(session, monkeypatch, tmp_path, "artifact-rollback-owner")
        second, _changed = append_revision(session, thread, first, "second", actor="assistant")
        session.commit()
        thread_id, first_id, second_id = thread.id, first.id, second.id
        blobs = sorted(p.name for p in (tmp_path / "assistant_artifacts" / str(thread_id)).iterdir())
        assert len(blobs) == 2

    with SessionLocal() as session:
        delete_artifact(session, thread_id, first_id)
        session.rollback()

    with SessionLocal() as session:
        assert [item.id for item in list_artifacts(session, thread_id)] == [second_id]
        assert sorted(p.name for p in (tmp_path / "assistant_artifacts" / str(thread_id)).iterdir()) == blobs
    get_settings.cache_clear()
