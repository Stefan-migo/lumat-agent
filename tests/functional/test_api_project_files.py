from pathlib import Path

from app.db import SessionLocal
from app.models import KbDocument, Project, ProjectFile


def _login(client, make_user, username):
    owner_id = make_user(username, "project-files-pass")
    response = client.post("/panel/api/login", json={"username": username, "password": "project-files-pass"})
    assert response.status_code == 200
    return owner_id


def _seed_project(owner_id, slug):
    with SessionLocal() as session:
        project = Project(slug=slug, name=slug, purpose=f"Purpose {slug}", purpose_embedding=[0.0] * 384, owner_id=owner_id)
        session.add(project)
        session.commit()
        return project.slug


def test_upload_list_and_download_project_file(client, make_user, monkeypatch, tmp_path):
    from app.config import get_settings
    owner_id = make_user("project-file-owner", "project-files-pass")
    slug = _seed_project(owner_id, "project-file-api")
    client.post("/panel/api/login", json={"username": "project-file-owner", "password": "project-files-pass"})
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    uploaded = client.post(f"/panel/api/projects/{slug}/files", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert uploaded.status_code == 201, uploaded.text
    metadata = uploaded.json()["file"]
    assert metadata["filename"] == "notes.txt"
    assert metadata["size"] == 5
    assert "stored_path" not in metadata
    listed = client.get(f"/panel/api/projects/{slug}/files")
    assert listed.status_code == 200
    assert listed.json()["files"] == [metadata]
    downloaded = client.get(f"/panel/api/projects/{slug}/files/{metadata['id']}/download")
    assert downloaded.status_code == 200
    assert downloaded.content == b"hello"
    assert "notes.txt" in downloaded.headers["content-disposition"]
    get_settings.cache_clear()


def test_upload_text_file_stays_local_without_kb_document(client, make_user, monkeypatch, tmp_path):
    """S12: the upload stores the file and leaves the project KB alone.

    The project knowledge base is fed only from the "Conocimiento del proyecto" card, so an
    upload must not create a document, must report a null `kb_document_id`, and must still keep
    the bytes on disk.
    """
    from app.config import get_settings
    owner_id = make_user("project-file-kb-owner", "project-files-pass")
    slug = _seed_project(owner_id, "project-file-kb")
    client.post("/panel/api/login", json={"username": "project-file-kb-owner", "password": "project-files-pass"})
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    uploaded = client.post(
        f"/panel/api/projects/{slug}/files",
        files={"file": ("manual.txt", b"Project-only safety instructions for the heater.", "text/plain")},
    )
    assert uploaded.status_code == 201, uploaded.text
    body = uploaded.json()["file"]
    assert body["kb_document_id"] is None
    assert body["status"] == "ready"
    with SessionLocal() as session:
        project = session.query(Project).filter_by(slug=slug).one()
        assert session.query(KbDocument).filter_by(project_id=project.id).count() == 0
        stored = session.query(ProjectFile).filter_by(project_id=project.id, filename="manual.txt").one()
        assert stored.kb_document_id is None
        assert Path(stored.stored_path).read_bytes() == b"Project-only safety instructions for the heater."
    get_settings.cache_clear()


def test_project_file_api_requires_auth_and_owner_scoping(client, make_user):
    owner_id = make_user("project-file-owner-a", "project-files-pass")
    make_user("project-file-owner-b", "project-files-pass")
    slug = _seed_project(owner_id, "project-file-private")
    assert client.get(f"/panel/api/projects/{slug}/files").status_code == 401
    client.post("/panel/api/login", json={"username": "project-file-owner-b", "password": "project-files-pass"})
    assert client.post(f"/panel/api/projects/{slug}/files", files={"file": ("x.txt", b"x", "text/plain")}).status_code == 404
    assert client.get(f"/panel/api/projects/{slug}/files").status_code == 404
    assert client.get(f"/panel/api/projects/{slug}/files/1/download").status_code == 404


def test_project_file_api_rejects_invalid_files_and_missing_project(client, make_user, monkeypatch):
    from app.config import get_settings
    owner_id = _login(client, make_user, "project-file-invalid")
    assert client.get("/panel/api/projects/missing/files").status_code == 404
    unsupported = client.post("/panel/api/projects/missing/files", files={"file": ("x.exe", b"x", "application/octet-stream")})
    assert unsupported.status_code == 404
    slug = _seed_project(owner_id, "project-file-invalid")
    bad = client.post(f"/panel/api/projects/{slug}/files", files={"file": ("x.exe", b"x", "application/octet-stream")})
    assert bad.status_code == 400
    monkeypatch.setenv("PROJECT_FILE_MAX_BYTES", "2")
    get_settings.cache_clear()
    oversized = client.post(f"/panel/api/projects/{slug}/files", files={"file": ("x.txt", b"large", "text/plain")})
    assert oversized.status_code == 400
    get_settings.cache_clear()


def test_move_project_file_between_folder_and_root(client, make_user, monkeypatch, tmp_path):
    from app.config import get_settings
    owner_id = _login(client, make_user, "project-file-move")
    slug = _seed_project(owner_id, "project-file-move")
    monkeypatch.setenv("MEDIA_DIR", str(tmp_path))
    get_settings.cache_clear()
    folder = client.post(f"/panel/api/projects/{slug}/folders", json={"name": "Diseño"})
    assert folder.status_code == 201, folder.text
    folder_id = folder.json()["folder"]["id"]
    uploaded = client.post(f"/panel/api/projects/{slug}/files", files={"file": ("notes.txt", b"hello", "text/plain")})
    file_id = uploaded.json()["file"]["id"]

    moved = client.patch(f"/panel/api/projects/{slug}/files/{file_id}", json={"folder_id": folder_id})
    assert moved.status_code == 200, moved.text
    assert moved.json()["file"]["folder_id"] == folder_id

    back = client.patch(f"/panel/api/projects/{slug}/files/{file_id}", json={"folder_id": None})
    assert back.status_code == 200
    assert back.json()["file"]["folder_id"] is None

    assert client.patch(f"/panel/api/projects/{slug}/files/{file_id}", json={"folder_id": 999}).status_code == 400
    assert client.patch(f"/panel/api/projects/{slug}/files/999", json={"folder_id": folder_id}).status_code == 404
    get_settings.cache_clear()
