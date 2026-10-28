"""The dev-settings contract both repo-root scripts rely on.

`app.config.Settings` is fail-fast: five webhook/panel values are required even
though neither `seed_kb_docs.py` nor `conv_eval.py` touches the webhook or the
panel. `ensure_dev_env` fills only what is missing, so a documented command runs
from the repo root while a real environment always wins.
"""

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import seed_kb_docs  # noqa: E402

DEV_SETTINGS = (
    "APP_SECRET",
    "VERIFY_TOKEN",
    "META_ACCESS_TOKEN",
    "META_PHONE_NUMBER_ID",
    "PANEL_SESSION_SECRET",
)


def reload_seed(monkeypatch):
    monkeypatch.setattr(seed_kb_docs, "_DEV_ONLY_SETTINGS", DEV_SETTINGS)
    return importlib.reload(seed_kb_docs)


def test_missing_settings_are_filled_with_placeholders(monkeypatch):
    import os

    for name in DEV_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    reload_seed(monkeypatch)
    for name in DEV_SETTINGS:
        assert os.environ[name] == f"conv-eval-{name.lower()}"


def test_a_real_value_is_never_overwritten(monkeypatch):
    import os

    for name in DEV_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("APP_SECRET", "un-secreto-real")
    reload_seed(monkeypatch)
    assert os.environ["APP_SECRET"] == "un-secreto-real"
    assert os.environ["VERIFY_TOKEN"] == "conv-eval-verify_token"


def test_the_helper_is_idempotent(monkeypatch):
    import os

    for name in DEV_SETTINGS:
        monkeypatch.delenv(name, raising=False)
    reload_seed(monkeypatch)
    before = {name: os.environ[name] for name in DEV_SETTINGS}
    reload_seed(monkeypatch)
    assert {name: os.environ[name] for name in DEV_SETTINGS} == before


def test_no_credential_is_ever_invented(monkeypatch):
    import os

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    reload_seed(monkeypatch)
    assert "DEEPSEEK_API_KEY" not in os.environ


# The release check in docs/ops.md §2.5 runs `scripts/seed_kb_docs.py` INSIDE the
# deployed container, so the image must carry the script and the documents it
# seeds. Neither was copied before, and `docs/` is excluded by `.dockerignore`:
# the check could not run, and nothing failed until someone tried it on the VPS.
def test_prod_image_ships_the_seed_script_and_the_kb_documents():
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY scripts/ scripts/" in dockerfile
    assert "COPY docs/kb/ docs/kb/" in dockerfile


def test_dockerignore_keeps_docs_kb_in_the_build_context():
    dockerignore = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8")
    lines = [line.strip() for line in dockerignore.splitlines()]
    assert "docs/" in lines
    assert "!docs/kb/" in lines
    assert "!docs/kb/**" in lines
    # A re-inclusion that comes BEFORE the exclusion it undoes would silently
    # reintroduce the failure: docker applies these in order, last match wins.
    assert lines.index("!docs/kb/**") > lines.index("docs/")


# The seed decides "already consistent" or "drifted" from `content_digest`. A
# document edited in the panel comes back with hard line breaks mid-sentence and
# indented lines (the textarea wraps), and the digest used to treat that as a
# different document: measured on production doc 44, which sat at version 5 with
# the right text and would have been re-created as a duplicate on the next seed.
def test_a_rewrapped_document_is_the_same_document():
    unwrapped = (
        "**Otras comunas.** Si estás fuera de esas comunas, un asesor coordina "
        "la visita según disponibilidad."
    )
    rewrapped = (
        "   **Otras comunas.** Si estás fuera de esas comunas, un asesor coordina\n"
        "   la visita según disponibilidad.\n"
    )

    assert seed_kb_docs.content_digest(rewrapped) == seed_kb_docs.content_digest(unwrapped)


def test_a_real_edit_still_changes_the_digest():
    before = "Las visitas se agendan de lunes a viernes."
    after = "Las visitas se agendan de lunes a sábado."

    assert seed_kb_docs.content_digest(before) != seed_kb_docs.content_digest(after)


def test_word_order_still_matters():
    assert seed_kb_docs.content_digest("sábado domingos") != seed_kb_docs.content_digest(
        "domingos sábado"
    )


def test_repeated_blank_lines_and_indentation_change_nothing():
    plain = "uno\ndos\ntres"
    noisy = "\n\n   uno\n\n      dos\n   tres\n\n"

    assert seed_kb_docs.content_digest(plain) == seed_kb_docs.content_digest(noisy)
