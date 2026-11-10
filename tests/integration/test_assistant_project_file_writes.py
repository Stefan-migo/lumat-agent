import hashlib
from pathlib import Path

import pytest
from sqlalchemy import select

from app.chat.assistant.approval import consume_approval, issue_approval
from app.chat.assistant.tools.registry import ToolValidationError, execute_tool
from app.config import get_settings
from app.db import SessionLocal
from app.models import AssistantArtifact, AuditLog, InternalChatThread, Project, ProjectFile, ProjectFolder, User
from app.services import assistant_artifacts
from app.services.project_files import store_project_file
from app.services.users import hash_password


def _setup(session, slug="project-write", *, project=True):
    owner = User(username=f"owner-{slug}", password_hash=hash_password("pass"), role="admin")
    session.add(owner)
    session.flush()
    workspace = None
    if project:
        workspace = Project(
            slug=slug, name=slug, purpose="project file write tests",
            purpose_embedding=[0.0] * 384, owner_id=owner.id,
        )
        session.add(workspace)
        session.flush()
    thread = InternalChatThread(user_id=owner.id, proyecto=slug if project else "default")
    session.add(thread)
    session.flush()
    return owner, workspace, thread


def _approval(name, arguments):
    from app.chat.assistant.tools.registry import get_tool

    normalized = get_tool(name).args_model.model_validate(arguments).model_dump()
    approval = issue_approval({"tool": name, "arguments": normalized})
    assert consume_approval(approval, approval["token"])
    return approval


def _run(session, owner, thread, name, arguments):
    approval = _approval(name, arguments)
    return execute_tool(
        session, name, arguments, approval=approval, owner_id=owner.id,
        trusted_thread_id=thread.id, role="admin", whitelist={name},
    )


def test_save_stores_text_at_project_root_and_existing_root_folder():
    with SessionLocal() as session:
        owner, project, thread = _setup(session)
        folder = ProjectFolder(project_id=project.id, parent_id=None, name="reports")
        session.add(folder)
        session.flush()

        root_result = _run(session, owner, thread, "project_file.save", {"filename": "root.md", "content": "root text"})
        folder_result = _run(session, owner, thread, "project_file.save", {
            "filename": "folder.csv", "content": "a,b", "folder": "reports",
        })
        root_row = session.get(ProjectFile, root_result["result"]["file_id"])
        folder_row = session.get(ProjectFile, folder_result["result"]["file_id"])
        assert root_result["status"] == folder_result["status"] == "completed"
        assert root_row.folder_id is None
        assert folder_row.folder_id == folder.id
        assert Path(root_row.stored_path).read_bytes() == b"root text"
        assert Path(folder_row.stored_path).read_bytes() == b"a,b"
        audit = session.scalar(select(AuditLog).where(
            AuditLog.action == "project_file.assistant_saved", AuditLog.entity_id == str(root_row.id),
        ))
        assert audit is not None
        assert audit.actor == "assistant"
        assert audit.after == {"project_id": project.id, "filename": "root.md", "size": 9, "folder_id": None}
        session.rollback()


def test_save_rejects_non_text_missing_project_and_missing_folder():
    with SessionLocal() as session:
        owner, project, thread = _setup(session)
        for args in (
            {"filename": "image.png", "content": "x"},
            {"filename": "missing.md", "content": "x", "folder": "absent"},
        ):
            approval = issue_approval({"tool": "project_file.save", "arguments": args})
            assert consume_approval(approval, approval["token"])
            with pytest.raises(ToolValidationError):
                execute_tool(session, "project_file.save", args, approval=approval, owner_id=owner.id,
                             trusted_thread_id=thread.id, role="admin")
        no_project_owner, _workspace, no_project_thread = _setup(session, "projectless", project=False)
        args = {"filename": "notes.md", "content": "x"}
        approval = _approval("project_file.save", args)
        with pytest.raises(ToolValidationError, match="thread has no project"):
            execute_tool(session, "project_file.save", args, approval=approval, owner_id=no_project_owner.id,
                         trusted_thread_id=no_project_thread.id, role="admin")
        session.rollback()


def test_update_replaces_same_row_and_identical_content_is_noop():
    with SessionLocal() as session:
        owner, project, thread = _setup(session)
        row = store_project_file(session, project, owner, "notes.md", "text/markdown", b"before")
        old_digest = row.sha256
        result = _run(session, owner, thread, "project_file.update", {"file_id": row.id, "content": "after"})
        assert result["status"] == "completed"
        backup_artifact_id = result["result"]["backup_artifact_id"]
        assert result["result"] == {
            "file_id": row.id, "filename": "notes.md", "size": 5, "changed": True,
            "backup_artifact_id": backup_artifact_id,
        }
        assert session.get(ProjectFile, row.id) is row
        assert row.sha256 == hashlib.sha256(b"after").hexdigest()
        assert row.sha256 != old_digest
        assert Path(row.stored_path).read_bytes() == b"after"
        audit = session.scalar(select(AuditLog).where(
            AuditLog.action == "project_file.assistant_updated", AuditLog.entity_id == str(row.id),
        ))
        assert audit is not None
        assert audit.actor == "assistant"
        assert audit.after == {
            "project_id": project.id, "file_id": row.id, "filename": "notes.md",
            "size": 5, "previous_sha256": old_digest, "sha256": row.sha256,
            "backup_artifact_id": backup_artifact_id,
        }
        original_sha = row.sha256
        original_path = Path(row.stored_path).read_bytes()
        audit_count = session.query(AuditLog).filter_by(
            action="project_file.assistant_updated", entity_id=str(row.id),
        ).count()
        no_op = _run(session, owner, thread, "project_file.update", {"file_id": row.id, "content": "after"})
        assert no_op["result"] == {"file_id": row.id, "filename": "notes.md", "size": 5, "changed": False}
        assert row.sha256 == original_sha
        assert Path(row.stored_path).read_bytes() == original_path
        assert session.query(AuditLog).filter_by(
            action="project_file.assistant_updated", entity_id=str(row.id),
        ).count() == audit_count
        session.rollback()


def test_update_backs_up_previous_content_as_thread_artifact_and_publishes_it():
    with SessionLocal() as session:
        owner, project, thread = _setup(session, "update-backup")
        row = store_project_file(session, project, owner, "notes.md", "text/markdown", b"previous text")

        result = _run(session, owner, thread, "project_file.update", {"file_id": row.id, "content": "new text"})

        backup = session.get(AssistantArtifact, result["result"]["backup_artifact_id"])
        assert backup.thread_id == thread.id
        assert backup.filename == "notes.bak.md"
        assert Path(backup.stored_path).read_bytes() == b"previous text"
        published = session.scalar(select(ProjectFile).where(
            ProjectFile.project_id == project.id,
            ProjectFile.source_artifact_root_id == backup.root_id,
        ))
        outputs = session.scalar(select(ProjectFolder).where(
            ProjectFolder.project_id == project.id, ProjectFolder.name == "outputs",
            ProjectFolder.parent_id.is_(None),
        ))
        assert outputs is not None
        assert published.folder_id == outputs.id
        assert Path(published.stored_path).read_bytes() == b"previous text"
        assert Path(row.stored_path).read_bytes() == b"new text"
        session.rollback()


def test_update_noop_creates_no_backup_or_outputs_file():
    with SessionLocal() as session:
        owner, project, thread = _setup(session, "update-noop-backup")
        row = store_project_file(session, project, owner, "notes.md", "text/markdown", b"same text")

        result = _run(session, owner, thread, "project_file.update", {"file_id": row.id, "content": "same text"})

        assert result["result"]["changed"] is False
        assert session.scalar(select(AssistantArtifact).where(AssistantArtifact.thread_id == thread.id)) is None
        assert session.scalar(select(ProjectFolder).where(
            ProjectFolder.project_id == project.id, ProjectFolder.name == "outputs",
        )) is None
        assert session.scalar(select(ProjectFile).where(ProjectFile.project_id == project.id,
                                                        ProjectFile.filename == "notes.bak.md")) is None
        session.rollback()


def test_update_missing_blob_fails_closed_and_leaves_row_unchanged(tmp_path):
    with SessionLocal() as session:
        owner, project, thread = _setup(session, "update-missing-blob")
        row = store_project_file(session, project, owner, "notes.md", "text/markdown", b"previous")
        row.stored_path = str(tmp_path / "missing-blob.md")
        session.flush()
        original = (row.stored_path, row.size, row.sha256)

        with pytest.raises(ToolValidationError, match="stored project file content is unavailable"):
            _run(session, owner, thread, "project_file.update", {"file_id": row.id, "content": "replacement"})

        assert (row.stored_path, row.size, row.sha256) == original
        session.rollback()


def test_update_refuses_when_backup_cannot_be_stored(monkeypatch):
    with SessionLocal() as session:
        owner, project, thread = _setup(session, "update-backup-failure")
        row = store_project_file(session, project, owner, "notes.md", "text/markdown", b"previous")
        original_bytes = Path(row.stored_path).read_bytes()
        original_size = row.size
        original_sha256 = row.sha256

        def fail_backup(*_args, **_kwargs):
            raise ValueError("artifact size exceeds the configured limit")

        monkeypatch.setattr(assistant_artifacts, "save_or_append", fail_backup)
        with pytest.raises(ToolValidationError, match="artifact size exceeds the configured limit"):
            _run(session, owner, thread, "project_file.update", {"file_id": row.id, "content": "replacement"})

        assert Path(row.stored_path).read_bytes() == original_bytes
        assert row.size == original_size
        assert row.sha256 == original_sha256
        session.rollback()


def test_update_rejects_other_project_artifact_published_and_non_text_files():
    with SessionLocal() as session:
        owner, project, thread = _setup(session, "update-owner")
        other_owner, other_project, _other_thread = _setup(session, "update-other")
        other_file = store_project_file(session, other_project, other_owner, "other.txt", "text/plain", b"other")
        published = store_project_file(session, project, owner, "published.md", "text/markdown", b"published")
        published.source_artifact_root_id = 42
        image = ProjectFile(
            project_id=project.id, owner_id=owner.id, filename="image.png", content_type="image/png",
            size=1, sha256=hashlib.sha256(b"x").hexdigest(), stored_path="unused", status="ready",
        )
        session.add(image)
        session.flush()
        for file_id, expected in (
            (other_file.id, "project file not found"),
            (published.id, "published from an artifact"),
            (image.id, "text files"),
        ):
            args = {"file_id": file_id, "content": "replacement"}
            approval = _approval("project_file.update", args)
            with pytest.raises(ToolValidationError, match=expected):
                execute_tool(session, "project_file.update", args, approval=approval, owner_id=owner.id,
                             trusted_thread_id=thread.id, role="admin")
        session.rollback()
    get_settings.cache_clear()
