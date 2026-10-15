"""The `view_image` tool returns on-demand image handles for the assistant (S5)."""

import pytest

from app.chat.assistant.tools.registry import (
    ToolValidationError,
    execute_tool,
    get_tool,
    is_tool_allowed_for_role,
)
from app.db import SessionLocal
from app.models import AssistantAttachment, Project, ProjectFile, User
from app.services.agent_chat import create_thread
from app.services.prompts import load_assistant_config


def _png(path, name="photo.png"):
    target = path / name
    target.write_bytes(b"\x89PNG\r\n\x1a\n-image-bytes")
    return target


def test_view_image_is_registered_read_only_and_authorized(make_user):
    make_user("view-image-reg", "pass", role="admin")

    whitelist = load_assistant_config().tools_whitelist
    assert get_tool("view_image").read_only is True
    assert "view_image" in whitelist
    assert is_tool_allowed_for_role("view_image", "admin") is True
    assert is_tool_allowed_for_role("view_image", "operador") is True
    assert is_tool_allowed_for_role("view_image", "tecnico") is False


def test_view_image_returns_a_handle_for_a_project_image(make_user, tmp_path):
    owner_id = make_user("view-image-project", "pass", role="admin")
    source = _png(tmp_path, "diagram.png")
    with SessionLocal() as session:
        project = Project(
            slug="view-image-project", name="Project", purpose="A",
            purpose_embedding=[0.0] * 384, owner_id=owner_id,
        )
        session.add(project)
        session.flush()
        row = ProjectFile(
            project_id=project.id, owner_id=owner_id, filename="diagram.png", content_type="image/png",
            size=source.stat().st_size, sha256="a" * 64, stored_path=str(source), status="ready",
        )
        session.add(row)
        session.flush()
        project_id, file_id = project.id, row.id
        session.commit()

    with SessionLocal() as session:
        result = execute_tool(
            session, "view_image", {"source": "project", "id": file_id},
            role="admin", owner_id=owner_id, project_id=project_id, trusted_thread_id=None,
        )

    assert result["status"] == "completed"
    assert result["read_only"] is True
    assert result["result"]["image"] == {
        "source": "project", "id": file_id, "filename": "diagram.png", "mime": "image/png",
    }


def test_view_image_returns_a_handle_for_a_thread_image(make_user, tmp_path):
    owner_id = make_user("view-image-thread", "pass", role="admin")
    source = _png(tmp_path, "shot.png")
    with SessionLocal() as session:
        user = session.get(User, owner_id)
        thread = create_thread(session, user)
        row = AssistantAttachment(
            thread_id=thread.id, filename="shot.png", kind="image", content_type="image/png",
            size=source.stat().st_size, sha256="b" * 64, stored_path=str(source),
        )
        session.add(row)
        session.flush()
        thread_id, attachment_id = thread.id, row.id
        session.commit()

    with SessionLocal() as session:
        result = execute_tool(
            session, "view_image", {"source": "thread", "id": attachment_id},
            role="admin", owner_id=owner_id, trusted_thread_id=thread_id,
        )

    assert result["status"] == "completed"
    assert result["result"]["image"] == {
        "source": "thread", "id": attachment_id, "filename": "shot.png", "mime": "image/png",
    }


def test_view_image_rejects_a_non_image_project_file(make_user, tmp_path):
    owner_id = make_user("view-image-nonimage", "pass", role="admin")
    text = tmp_path / "notes.txt"
    text.write_bytes(b"not an image")
    with SessionLocal() as session:
        project = Project(
            slug="view-image-nonimage", name="Project", purpose="A",
            purpose_embedding=[0.0] * 384, owner_id=owner_id,
        )
        session.add(project)
        session.flush()
        row = ProjectFile(
            project_id=project.id, owner_id=owner_id, filename="notes.txt", content_type="text/plain",
            size=text.stat().st_size, sha256="c" * 64, stored_path=str(text), status="ready",
        )
        session.add(row)
        session.flush()
        project_id, file_id = project.id, row.id
        session.commit()

    with SessionLocal() as session:
        with pytest.raises(ToolValidationError, match="not a viewable image"):
            execute_tool(
                session, "view_image", {"source": "project", "id": file_id},
                role="admin", owner_id=owner_id, project_id=project_id, trusted_thread_id=None,
            )


def test_view_image_rejects_a_foreign_thread_image(make_user, tmp_path):
    victim_id = make_user("view-image-victim", "pass", role="admin")
    attacker_id = make_user("view-image-attacker", "pass", role="admin")
    source = _png(tmp_path, "private.png")
    with SessionLocal() as session:
        victim = session.get(User, victim_id)
        attacker = session.get(User, attacker_id)
        victim_thread = create_thread(session, victim)
        attacker_thread = create_thread(session, attacker)
        row = AssistantAttachment(
            thread_id=victim_thread.id, filename="private.png", kind="image", content_type="image/png",
            size=source.stat().st_size, sha256="d" * 64, stored_path=str(source),
        )
        session.add(row)
        session.flush()
        attacker_thread_id, attachment_id = attacker_thread.id, row.id
        session.commit()

    with SessionLocal() as session:
        with pytest.raises(ToolValidationError, match="not found"):
            execute_tool(
                session, "view_image", {"source": "thread", "id": attachment_id},
                role="admin", owner_id=attacker_id, trusted_thread_id=attacker_thread_id,
            )
