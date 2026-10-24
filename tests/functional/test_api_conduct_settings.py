"""S18 panel API — the three conduct surfaces the panel had no read for.

F3/F4 shipped `chat.conduct`, `capture.questions` and `reply.texts` with write
routes only. F6 exposes the effective value of each so the panel can show what
the bot is actually doing, not just what the owner typed.

Covers:
- GET /settings returns `conduct` with the closed option lists and `customized`
- `capture_questions` is the effective wording, limited to the effective order
- `reply_texts` is the effective text per key plus the slots it accepts
- `capture.questions` rejects slots: nothing renders that text (F6 contract)
"""

from __future__ import annotations

import pytest

from pathlib import Path

from app.chat.nodes.capture import CAPTURE_FIELDS, CAPTURE_FIELD_LABELS, _ask_text, _field_questions
from app.db import SessionLocal  # noqa: E402
from app.models import Settings  # noqa: E402
from app.services import settings as settings_service  # noqa: E402

CONDUCT = "/panel/api/settings/conduct"
CAPTURE_QUESTIONS = "/panel/api/settings/capture-questions"
REPLY_TEXTS = "/panel/api/settings/reply-texts"


def _login(client, username: str = "adm", password: str = "adm-pass") -> None:
    resp = client.post(
        "/panel/api/login",
        json={"username": username, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 200, f"api login must succeed: {resp.status_code} {resp.text}"


@pytest.fixture
def admin(client, make_user):
    make_user("adm", "adm-pass", role="admin")
    _login(client)
    return client


def _settings(admin) -> dict:
    return admin.get("/panel/api/settings").json()


# --- conduct -----------------------------------------------------------------


def test_conduct_is_exposed_with_its_closed_options(admin):
    conduct = _settings(admin)["conduct"]

    assert conduct["orden"] == settings_service.CHAT_CONDUCT_DEFAULTS["orden"]
    assert conduct["max_preguntas_por_mensaje"] == 1
    assert conduct["derivaciones"] == list(settings_service.CONDUCT_DERIVACIONES)
    assert conduct["customized"] is False
    assert [field["value"] for field in conduct["options"]["fields"]] == [
        field for field, _ in CAPTURE_FIELDS
    ]
    assert conduct["options"]["fields"][0]["label"] == CAPTURE_FIELD_LABELS["failure"]
    assert conduct["options"]["max_preguntas_por_mensaje"] == [1, 2]
    # S4: the closed list is exactly the rules with a reader.
    assert conduct["options"]["derivaciones"] == list(
        settings_service.CONDUCT_DERIVACIONES
    )


def test_conduct_save_is_visible_in_the_settings_payload(admin):
    changed = {
        **settings_service.CHAT_CONDUCT_DEFAULTS,
        "orden": ["failure", "equipment", "comuna", "availability", "name"],
        "max_preguntas_por_mensaje": 2,
        "derivaciones": ["cobertura"],
    }
    assert admin.post(CONDUCT, json={"conduct": changed}, follow_redirects=False).status_code == 200

    conduct = _settings(admin)["conduct"]
    assert conduct["orden"] == changed["orden"]
    assert conduct["max_preguntas_por_mensaje"] == 2
    assert conduct["derivaciones"] == ["cobertura"]
    assert conduct["customized"] is True


# --- capture questions -------------------------------------------------------


def test_capture_questions_expose_the_effective_wording(admin):
    payload = _settings(admin)["capture_questions"]

    defaults = dict(CAPTURE_FIELDS)
    assert list(payload["questions"]) == settings_service.CHAT_CONDUCT_DEFAULTS["orden"]
    assert payload["questions"]["comuna"] == defaults["comuna"]
    assert payload["customized"] is False


def test_capture_questions_follow_the_effective_order(admin):
    order = ["failure", "comuna", "name"]
    admin.post(
        CONDUCT,
        json={"conduct": {**settings_service.CHAT_CONDUCT_DEFAULTS, "orden": order}},
        follow_redirects=False,
    )

    payload = _settings(admin)["capture_questions"]

    assert list(payload["questions"]) == order


def test_capture_questions_save_is_visible_in_the_settings_payload(admin):
    order = settings_service.CHAT_CONDUCT_DEFAULTS["orden"]
    questions = {field: f"¿{field}?" for field in order}
    assert (
        admin.post(
            CAPTURE_QUESTIONS, json={"questions": questions}, follow_redirects=False
        ).status_code
        == 200
    )

    payload = _settings(admin)["capture_questions"]
    assert payload["questions"] == questions
    assert payload["customized"] is True


def test_capture_questions_reject_slots_without_persisting(admin):
    order = settings_service.CHAT_CONDUCT_DEFAULTS["orden"]
    questions = {field: f"¿{field}?" for field in order}
    questions["failure"] = "Hola {{nombre}}, cuéntame la falla."

    resp = admin.post(CAPTURE_QUESTIONS, json={"questions": questions}, follow_redirects=False)

    assert resp.status_code == 400
    with SessionLocal() as session:
        assert session.get(Settings, settings_service.CAPTURE_QUESTIONS_KEY) is None


# --- reply texts -------------------------------------------------------------


def test_reply_texts_expose_the_effective_text_and_slots(admin):
    payload = _settings(admin)["reply_texts"]

    assert payload["texts"] == settings_service.REPLY_TEXT_DEFAULTS
    assert sorted(payload["texts"]) == sorted(settings_service.REPLY_TEXT_DEFAULTS)
    assert payload["slots"]["booking_offer"] == ["opciones"]
    assert payload["slots"]["manage_kept"] == []
    assert payload["customized"] is False


def test_reply_texts_save_is_visible_in_the_settings_payload(admin):
    texts = {**settings_service.REPLY_TEXT_DEFAULTS, "manage_kept": "De acuerdo, quedó igual."}
    assert admin.post(REPLY_TEXTS, json={"texts": texts}, follow_redirects=False).status_code == 200

    payload = _settings(admin)["reply_texts"]
    assert payload["texts"]["manage_kept"] == "De acuerdo, quedó igual."
    assert payload["customized"] is True


def test_every_derivation_the_panel_renders_has_a_reader(admin):
    """S10/S18: a checkbox the panel shows must be read by app code.

    T10 listed five rules and only `cobertura` gated anything; S4 removed the
    other four from the closed list instead of keeping them as switches with no
    effect. This guard fails if the panel ever renders a rule the code ignores.
    """
    root = Path(__file__).resolve().parents[2]
    code = "\n".join(
        path.read_text()
        for path in (root / "app").rglob("*.py")
        if path.name != "settings.py"
    )

    exposed = _settings(admin)["conduct"]["options"]["derivaciones"]

    assert exposed, "the panel must render at least one derivation rule"
    assert [rule for rule in exposed if rule not in code] == []


def test_a_legacy_slot_row_does_not_reach_the_client(admin):
    """F6 narrows `capture.questions` to plain text. A row saved before that
    (T7 accepted slots) must fall back to the shipped wording, not leak braces."""
    questions = {field: f"¿{field}?" for field in settings_service.CHAT_CONDUCT_DEFAULTS["orden"]}
    questions["failure"] = "{{nombre}}, cuéntame la falla."
    with SessionLocal() as session:
        session.add(Settings(key=settings_service.CAPTURE_QUESTIONS_KEY, value=dict(questions)))
        session.commit()

    payload = _settings(admin)["capture_questions"]["questions"]
    assert payload["failure"] == dict(CAPTURE_FIELDS)["failure"]
    assert payload["comuna"] == "¿comuna?"
    with SessionLocal() as session:
        assert "{{" not in _ask_text(["failure"], _field_questions(session))
