"""Partial project-file reads: offset/limit paging (S6)."""

from types import SimpleNamespace

import pytest

from app.chat.assistant.tools.registry import ToolValidationError, execute_tool
from app.services.project_files import MAX_FILE_TEXT_CHARS, read_file_text

_TEXT = "".join(str(index % 10) for index in range(50_000))


def _row(tmp_path, name="a.txt", content_type="text/plain"):
    source = tmp_path / name
    source.write_bytes(b"x")
    return SimpleNamespace(id=3, filename=name, content_type=content_type, size=1, stored_path=str(source))


def _patch_text(monkeypatch):
    monkeypatch.setattr("app.services.project_files.allowed_project_file", lambda *args, **kwargs: "txt")
    monkeypatch.setattr(
        "app.services.project_files.extract_document_text", lambda content, kind: _TEXT
    )


def test_read_file_text_slices_with_offset_and_limit(monkeypatch, tmp_path):
    _patch_text(monkeypatch)

    result = read_file_text(_row(tmp_path), offset=2, limit=4)

    assert result["text"] == _TEXT[2:6]
    assert result["chars"] == len(_TEXT)
    assert result["offset"] == 2
    assert result["limit"] == 4
    assert result["truncated"] is True
    assert result["next_offset"] == 6


def test_read_file_text_default_read_is_unchanged(monkeypatch, tmp_path):
    _patch_text(monkeypatch)

    result = read_file_text(_row(tmp_path))

    assert result["text"] == _TEXT[:MAX_FILE_TEXT_CHARS]
    assert result["chars"] == len(_TEXT)
    assert result["offset"] == 0
    assert result["limit"] == MAX_FILE_TEXT_CHARS
    assert result["truncated"] is True
    assert result["next_offset"] == MAX_FILE_TEXT_CHARS


def test_read_file_text_past_the_end_is_empty_and_final(monkeypatch, tmp_path):
    _patch_text(monkeypatch)

    result = read_file_text(_row(tmp_path), offset=len(_TEXT) + 10, limit=100)

    assert result["text"] == ""
    assert result["truncated"] is False
    assert result["next_offset"] is None


def test_read_file_text_chunks_reassemble_the_whole_file(monkeypatch, tmp_path):
    _patch_text(monkeypatch)
    row = _row(tmp_path)

    rebuilt = ""
    offset = 0
    while offset is not None:
        chunk = read_file_text(row, offset=offset, limit=4_000)
        rebuilt += chunk["text"]
        offset = chunk["next_offset"]

    assert rebuilt == _TEXT


def test_read_project_file_forwards_offset_and_limit(monkeypatch):
    gathered = {}

    def fake_read_file_text(row, *, offset=0, limit=MAX_FILE_TEXT_CHARS):
        gathered.update(offset=offset, limit=limit)
        return {"kind": "pdf", "text": "hi", "truncated": False, "chars": 2,
                "offset": offset, "limit": limit, "next_offset": None}

    monkeypatch.setattr("app.chat.assistant.tools.registry.project_files.owned_project",
                        lambda *args, **kwargs: SimpleNamespace(id=7, slug="gas"))
    monkeypatch.setattr("app.chat.assistant.tools.registry.project_files.get_project_file",
                        lambda *_args: SimpleNamespace(id=3, filename="a.pdf"))
    monkeypatch.setattr("app.chat.assistant.tools.registry.project_files.read_file_text", fake_read_file_text)

    result = execute_tool(
        SimpleNamespace(), "read_project_file", {"file_id": 3, "offset": 5, "limit": 10},
        owner_id=1, role="admin",
    )

    assert gathered == {"offset": 5, "limit": 10}
    assert result["result"]["text"] == "hi"


@pytest.mark.parametrize("arguments", [
    {"file_id": 3, "offset": -1},
    {"file_id": 3, "limit": 0},
    {"file_id": 3, "limit": MAX_FILE_TEXT_CHARS + 1},
])
def test_read_project_file_rejects_out_of_range_paging(arguments):
    with pytest.raises(ToolValidationError):
        execute_tool(SimpleNamespace(), "read_project_file", arguments, owner_id=1, role="admin")
