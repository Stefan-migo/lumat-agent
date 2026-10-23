"""The suite must never write into the repository's `media/` tree.

`media/` is a compose volume (`.gitignore:26-27`), so on a dev host it is owned by
root and not writable, while on a CI checkout it does not exist at all. A test
that falls back to the default `MEDIA_DIR="media"` therefore fails locally with
`PermissionError: media/projects` and silently creates a directory inside the
checkout on CI — green for the wrong reason.

`tests/conftest.py` forces an isolated directory for every test; this pins that
contract so a future edit cannot reintroduce writing into the working tree.
"""

from pathlib import Path

from app.config import get_settings

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_media_dir_resolves_outside_the_repository():
    media_dir = Path(get_settings().media_dir).resolve()
    assert REPO_ROOT not in media_dir.parents
    assert media_dir != (REPO_ROOT / "media").resolve()
