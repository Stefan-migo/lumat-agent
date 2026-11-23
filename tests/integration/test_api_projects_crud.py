from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.models import (
    AssistantArtifact, AssistantAttachment, DocumentFormat, InternalChatMessage,
    InternalChatThread, KbChunk, KbDocument, Memory, MemoryObservation, MemoryRelation,
    MemoryType, ObservationType, Project, ProjectAlias, ProjectAudit, ProjectFile,
    ProjectFolder, User,
)
from app.services.users import hash_password


def _project(session, owner_id: int, slug: str, *, status="active") -> Project:
    row = Project(slug=slug, name=slug.title(), purpose=f"Unique purpose {slug}", purpose_embedding=[0.0] * 384, owner_id=owner_id, status=status)
    session.add(row)
    session.flush()
    return row


def _login(client, username: str) -> None:
    response = client.post("/panel/api/login", json={"username": username, "password": "test-pass"})
    assert response.status_code == 200


def test_project_lifecycle_rename_and_owner_scoping(client):
    with SessionLocal() as session:
        owner = User(username="crud-owner", password_hash=hash_password("test-pass"), role="operador")
        other = User(username="crud-other", password_hash=hash_password("test-pass"), role="operador")
        session.add_all([owner, other])
        session.flush()
        project = _project(session, owner.id, "lifecycle")
        session.commit()
        owner_id, other_id = owner.id, other.id
    _login(client, "crud-other")
    assert client.post("/panel/api/projects/lifecycle/archive").status_code == 404
    client.post("/panel/api/logout")
    _login(client, "crud-owner")

    renamed = client.patch("/panel/api/projects/lifecycle", json={"name": "Operations"})
    assert renamed.status_code == 200
    assert renamed.json()["project"]["slug"] == "lifecycle"
    assert renamed.json()["project"]["name"] == "Operations"
    assert client.patch("/panel/api/projects/lifecycle", json={"name": "  "}).status_code == 400
    assert client.post("/panel/api/projects/lifecycle/archive").json()["project"]["status"] == "archived"
    assert client.post("/panel/api/projects/lifecycle/reactivate").json()["project"]["status"] == "active"
    with SessionLocal() as session:
        assert session.scalar(select(ProjectAudit).where(ProjectAudit.project_id == project.id, ProjectAudit.action == "archive"))
        assert session.scalar(select(ProjectAudit).where(ProjectAudit.project_id == project.id, ProjectAudit.action == "project.reactivate"))
        assert session.scalar(select(ProjectAlias).where(ProjectAlias.project_id == project.id, ProjectAlias.alias == "operations"))
        assert session.get(User, other_id) is not None
        assert owner_id == project.owner_id


def test_move_project_files_preserves_folder_tree_and_rejects_foreign_target(client):
    with SessionLocal() as session:
        owner = User(username="move-owner", password_hash=hash_password("test-pass"), role="operador")
        other = User(username="move-other", password_hash=hash_password("test-pass"), role="operador")
        session.add_all([owner, other])
        session.flush()
        source = _project(session, owner.id, "move-source")
        target = _project(session, owner.id, "move-target")
        foreign = _project(session, other.id, "move-foreign")
        root = ProjectFolder(project_id=source.id, name="Reports")
        session.add(root)
        session.flush()
        child = ProjectFolder(project_id=source.id, parent_id=root.id, name="Annual")
        session.add(child)
        session.flush()
        file = ProjectFile(project_id=source.id, owner_id=owner.id, filename="report.txt", content_type="text/plain", size=4, sha256="hash", stored_path="/test/report", status="ready", folder_id=child.id)
        session.add(file)
        session.commit()
        source_id, target_id, foreign_id, file_id = source.id, target.id, foreign.id, file.id
    _login(client, "move-owner")

    moved = client.post("/panel/api/projects/move-source/move-files", json={"target_slug": "move-target"})
    assert moved.status_code == 200
    assert moved.json() == {"ok": True, "files": 1, "folders": 2}
    assert client.post("/panel/api/projects/move-source/move-files", json={"target_slug": "move-foreign"}).status_code == 404
    with SessionLocal() as session:
        row = session.get(ProjectFile, file_id)
        assert row.project_id == target_id
        child_row = session.get(ProjectFolder, row.folder_id)
        root_row = session.get(ProjectFolder, child_row.parent_id)
        assert (root_row.project_id, root_row.name, child_row.name) == (target_id, "Reports", "Annual")
        assert session.scalar(select(ProjectFile).where(ProjectFile.project_id == source_id)) is None
        assert session.scalar(select(ProjectFolder).where(ProjectFolder.project_id == source_id)) is None
        assert session.get(Project, foreign_id) is not None


def test_project_deletion_impact_and_complete_owner_scoped_cleanup(client, tmp_path):
    with SessionLocal() as session:
        owner = User(username="impact-owner", password_hash=hash_password("test-pass"), role="operador")
        other = User(username="impact-other", password_hash=hash_password("test-pass"), role="operador")
        session.add_all([owner, other])
        session.flush()
        project = _project(session, owner.id, "impact-project")
        _project(session, other.id, "foreign-impact")
        folder = ProjectFolder(project_id=project.id, name="Reports")
        session.add(folder)
        session.flush()
        document = KbDocument(project_id=project.id, title="Guide", format=DocumentFormat.MD, content="Guide content")
        session.add(document)
        session.flush()
        session.add(KbChunk(document_id=document.id, version=1, chunk_index=0, content="chunk", embedding=[0.0] * 384))
        project_file_path = tmp_path / "project-file"
        project_file_path.write_text("file")
        session.add(ProjectFile(project_id=project.id, owner_id=owner.id, filename="file.txt", content_type="text/plain", size=4, sha256="hash", stored_path=str(project_file_path), folder_id=folder.id, kb_document_id=document.id))
        thread = InternalChatThread(user_id=owner.id, proyecto=project.slug, title="Thread")
        session.add(thread)
        session.flush()
        session.add(InternalChatMessage(thread_id=thread.id, author="user", content="hello"))
        artifact_path, attachment_path = tmp_path / "artifact", tmp_path / "attachment"
        artifact_path.write_text("artifact")
        attachment_path.write_text("attachment")
        session.add(AssistantArtifact(thread_id=thread.id, root_id=1, version=1, filename="out.txt", content_type="text/plain", size=8, sha256="hash", stored_path=str(artifact_path)))
        session.add(AssistantAttachment(thread_id=thread.id, filename="input.txt", kind="file", content_type="text/plain", size=10, sha256="hash", stored_path=str(attachment_path)))
        memory = Memory(owner_id=owner.id, proyecto=project.slug, scope="project", entity_id="one", tipo=MemoryType.DECISION, titulo="Owner memory", contenido="remember", embedding=[0.0] * 384, topic_key="owner")
        foreign_memory = Memory(owner_id=other.id, proyecto=project.slug, scope="project", entity_id="two", tipo=MemoryType.DECISION, titulo="Foreign memory", contenido="keep", embedding=[0.0] * 384, topic_key="foreign")
        session.add_all([memory, foreign_memory])
        session.flush()
        session.add(MemoryObservation(memory_id=memory.id, scope="project", entity_id="one", tipo=ObservationType.RIESGO))
        session.add(MemoryRelation(id_a=memory.id, id_b=foreign_memory.id, relation="related"))
        session.add(ProjectAlias(project_id=project.id, owner_id=owner.id, alias="impact alias"))
        session.add(ProjectAudit(project_id=project.id, actor="impact-owner", action="test", before={}, after={}))
        session.commit()
        slug, owner_id, foreign_memory_id = project.slug, owner.id, foreign_memory.id

    _login(client, "impact-owner")
    impact = client.get(f"/panel/api/projects/{slug}/deletion-impact")
    assert impact.status_code == 200
    assert client.get("/panel/api/projects/foreign-impact/deletion-impact").status_code == 404
    assert impact.json() == {"impact": {"threads": 1, "messages": 1, "files": 1, "folders": 1, "kb_documents": 1, "kb_chunks": 1, "memories": 1, "artifacts": 1, "attachments": 1}}
    assert client.get("/panel/api/projects/unknown/deletion-impact").status_code == 404
    assert client.get("/panel/api/projects/default/deletion-impact").status_code == 400

    deleted = client.delete(f"/panel/api/projects/{slug}")
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True, "deleted": impact.json()["impact"]}
    assert not project_file_path.exists()
    assert not artifact_path.exists()
    assert not attachment_path.exists()
    with SessionLocal() as session:
        assert session.scalar(select(Project).where(Project.slug == slug, Project.owner_id == owner_id)) is None
        assert session.scalar(select(InternalChatThread).where(InternalChatThread.proyecto == slug, InternalChatThread.user_id == owner_id)) is None
        assert session.scalar(select(KbDocument).where(KbDocument.project_id == project.id)) is None
        assert session.scalar(select(KbChunk).where(KbChunk.document_id == document.id)) is None
        assert session.scalar(select(Memory).where(Memory.owner_id == owner_id, Memory.proyecto == slug)) is None
        assert session.get(Memory, foreign_memory_id) is not None
        assert session.scalar(select(MemoryObservation).where(MemoryObservation.memory_id == memory.id)) is None
        assert session.scalar(select(MemoryRelation).where((MemoryRelation.id_a == memory.id) | (MemoryRelation.id_b == memory.id))) is None
        assert session.scalar(select(ProjectAlias).where(ProjectAlias.project_id == project.id)) is None
        assert session.scalar(select(ProjectAudit).where(ProjectAudit.project_id == project.id)) is None


def test_project_delete_protects_default_and_missing_or_foreign_projects(client):
    with SessionLocal() as session:
        owner = User(username="delete-owner", password_hash=hash_password("test-pass"), role="operador")
        other = User(username="delete-other", password_hash=hash_password("test-pass"), role="operador")
        session.add_all([owner, other])
        session.flush()
        _project(session, owner.id, "default")
        _project(session, owner.id, "delete-me")
        _project(session, other.id, "private-delete")
        session.commit()
    _login(client, "delete-owner")
    assert client.delete("/panel/api/projects/default").status_code == 400
    assert client.delete("/panel/api/projects/missing").status_code == 404
    assert client.delete("/panel/api/projects/private-delete").status_code == 404


def test_delete_removes_every_dependent_row_and_preview_matches(client, tmp_path):
    """S4: the preview, the response and the rows actually removed are the same census."""
    from datetime import datetime, timezone

    from sqlalchemy import func

    with SessionLocal() as session:
        owner = User(username="census-owner", password_hash=hash_password("test-pass"), role="operador")
        session.add(owner)
        session.flush()
        project = _project(session, owner.id, "census")
        folder = ProjectFolder(project_id=project.id, name="A")
        session.add(folder)
        session.flush()
        document = KbDocument(project_id=project.id, title="D", format=DocumentFormat.MD, content="c")
        session.add(document)
        session.flush()
        session.add(KbChunk(document_id=document.id, version=1, chunk_index=0, content="c", embedding=[0.0] * 384))
        file_blob = tmp_path / "file"; file_blob.write_text("x")
        artifact_blob = tmp_path / "artifact"; artifact_blob.write_text("a")
        attachment_blob = tmp_path / "attachment"; attachment_blob.write_text("t")
        session.add(ProjectFile(
            project_id=project.id, owner_id=owner.id, filename="f.txt", content_type="text/plain",
            size=1, sha256="h", stored_path=str(file_blob), folder_id=folder.id,
            kb_document_id=document.id,
        ))
        thread = InternalChatThread(user_id=owner.id, proyecto=project.slug)
        session.add(thread)
        session.flush()
        session.add(InternalChatMessage(thread_id=thread.id, author="user", content="m"))
        session.add(AssistantArtifact(
            thread_id=thread.id, root_id=1, version=1, filename="a", content_type="text/plain",
            size=1, sha256="h", stored_path=str(artifact_blob),
        ))
        session.add(AssistantAttachment(
            thread_id=thread.id, filename="t", kind="file", content_type="text/plain",
            size=1, sha256="h", stored_path=str(attachment_blob),
            deleted_at=datetime.now(timezone.utc),
        ))
        session.commit()
        project_id, thread_id, document_id = project.id, thread.id, document.id
    _login(client, "census-owner")

    impact = client.get("/panel/api/projects/census/deletion-impact").json()["impact"]
    assert impact == {
        "threads": 1, "messages": 1, "files": 1, "folders": 1, "kb_documents": 1, "kb_chunks": 1,
        "memories": 0, "artifacts": 1, "attachments": 1,
    }
    assert client.delete("/panel/api/projects/census").json()["deleted"] == impact

    with SessionLocal() as session:
        for statement in (
            select(func.count()).select_from(ProjectFile).where(ProjectFile.project_id == project_id),
            select(func.count()).select_from(ProjectFolder).where(ProjectFolder.project_id == project_id),
            select(func.count()).select_from(KbDocument).where(KbDocument.project_id == project_id),
            select(func.count()).select_from(KbChunk).where(KbChunk.document_id == document_id),
            select(func.count()).select_from(InternalChatMessage).where(InternalChatMessage.thread_id == thread_id),
            select(func.count()).select_from(AssistantArtifact).where(AssistantArtifact.thread_id == thread_id),
            select(func.count()).select_from(AssistantAttachment).where(AssistantAttachment.thread_id == thread_id),
        ):
            assert session.scalar(statement) == 0


def test_delete_rollback_keeps_blobs(tmp_path):
    """S4: a rolled-back delete unlinks nothing."""
    from app.services import projects as project_service

    blob = tmp_path / "keep"; blob.write_text("x")
    with SessionLocal() as session:
        owner = User(username="rollback-owner", password_hash=hash_password("test-pass"), role="operador")
        session.add(owner)
        session.flush()
        project = _project(session, owner.id, "rollback-me")
        session.add(ProjectFile(
            project_id=project.id, owner_id=owner.id, filename="k", content_type="text/plain",
            size=1, sha256="h", stored_path=str(blob),
        ))
        session.commit()
        project_service.delete_project(session, project, owner_id=owner.id, actor="rollback-owner")
        session.rollback()

    assert blob.exists()


def test_move_files_merges_same_name_folders_and_rescopes_kb(client):
    """S3: merge by name, keep the hierarchy, re-scope the KB document, audit the move."""
    with SessionLocal() as session:
        owner = User(username="move-owner", password_hash=hash_password("test-pass"), role="operador")
        session.add(owner)
        session.flush()
        source = _project(session, owner.id, "move-src")
        target = _project(session, owner.id, "move-tgt")
        reports = ProjectFolder(project_id=source.id, name="Reports")
        session.add(reports)
        session.flush()
        child = ProjectFolder(project_id=source.id, parent_id=reports.id, name="Q1")
        session.add(child)
        session.add(ProjectFolder(project_id=target.id, name="Reports"))
        session.flush()
        document = KbDocument(project_id=source.id, title="D", format=DocumentFormat.MD, content="c")
        session.add(document)
        session.flush()
        session.add_all([
            ProjectFile(
                project_id=source.id, owner_id=owner.id, filename="in.txt", content_type="text/plain",
                size=1, sha256="m1", stored_path="/nonexistent/a", folder_id=child.id,
                kb_document_id=document.id,
            ),
            ProjectFile(
                project_id=source.id, owner_id=owner.id, filename="top.txt", content_type="text/plain",
                size=1, sha256="m2", stored_path="/nonexistent/b",
            ),
        ])
        session.commit()
        target_id, document_id = target.id, document.id
    _login(client, "move-owner")

    assert client.post("/panel/api/projects/move-src/move-files", json={"target_slug": "move-tgt"}).json() == {
        "ok": True, "files": 2, "folders": 2,
    }
    with SessionLocal() as session:
        folders = session.scalars(select(ProjectFolder).where(ProjectFolder.project_id == target_id)).all()
        files = session.scalars(select(ProjectFile).where(ProjectFile.project_id == target_id)).all()
        assert sorted(folder.name for folder in folders) == ["Q1", "Reports"]
        assert session.get(KbDocument, document_id).project_id == target_id
        nested = next(file for file in files if file.filename == "in.txt")
        assert session.get(ProjectFolder, nested.folder_id).name == "Q1"
        assert session.scalar(select(ProjectAudit).where(
            ProjectAudit.project_id == target_id, ProjectAudit.action == "project.move_files"
        )) is not None


def test_move_and_lifecycle_rejections(client):
    """S3/S6/S7: negative rules, and no route reaches another owner's project."""
    from sqlalchemy import func

    with SessionLocal() as session:
        owner = User(username="reject-owner", password_hash=hash_password("test-pass"), role="operador")
        other = User(username="reject-other", password_hash=hash_password("test-pass"), role="operador")
        session.add_all([owner, other])
        session.flush()
        _project(session, owner.id, "default")
        _project(session, owner.id, "reject-src")
        _project(session, owner.id, "reject-archived", status="archived")
        _project(session, owner.id, "reject-taken")
        _project(session, other.id, "reject-foreign")
        session.commit()
    _login(client, "reject-owner")

    assert client.post("/panel/api/projects/reject-src/move-files", json={"target_slug": "reject-src"}).status_code == 400
    assert client.post("/panel/api/projects/reject-src/move-files", json={"target_slug": "reject-archived"}).status_code == 400
    assert client.post("/panel/api/projects/reject-foreign/reactivate").status_code == 404
    assert client.post("/panel/api/projects/default/archive").status_code == 400
    assert client.patch("/panel/api/projects/reject-src", json={"name": "reject-taken"}).status_code == 400
    with SessionLocal() as session:
        assert session.scalar(select(Project.name).where(Project.slug == "reject-src")) == "Reject-Src"
        assert session.scalar(select(func.count()).select_from(ProjectAlias).where(
            ProjectAlias.alias == "reject-taken"
        )) == 0
