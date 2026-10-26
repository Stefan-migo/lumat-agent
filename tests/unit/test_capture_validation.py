"""S2-S4 capture validation, deterministic acknowledgement and preventive skip."""
from contextlib import contextmanager

import pytest

from app.chat.nodes import capture as capture_node
from app.chat.state import ConversationState
from app.services.settings import REPLY_TEXT_DEFAULTS


class _Session:
    def get(self, *_args):
        return None


@pytest.fixture
def harness(monkeypatch):
    session = _Session()

    @contextmanager
    def session_scope():
        yield session

    monkeypatch.setattr(capture_node, "session_scope", session_scope)
    monkeypatch.setattr(capture_node, "get_conduct", lambda _session: {
        "orden": ["failure", "equipment", "comuna", "availability", "name", "email", "address"],
        "max_preguntas_por_mensaje": 1,
        "derivaciones": ["cobertura"],
    })
    monkeypatch.setattr(capture_node, "get_coverage_communes", lambda _session: ["Ñuñoa", "Las Condes"])
    monkeypatch.setattr(capture_node, "get_reply_texts", lambda _session: dict(REPLY_TEXT_DEFAULTS))
    monkeypatch.setattr(capture_node, "_persist_captured", lambda *_args: None)
    monkeypatch.setattr(capture_node, "get_capture_questions", lambda _session: {})
    return session


def make_state(text, *, captured, extracted=None):
    return ConversationState(
        customer_id=1, conversation_id=2, phone="+56912345678", captured=captured,
        extracted=extracted or {}, window=[{"text": text}],
    )


@pytest.mark.parametrize(
    "field,turn,extracted,bad_value",
    [
        pytest.param("comuna", "Soy Felipe. estoy con un problema con mi calefont, dejo de funcionar hace un par de dias", {"comuna": "Soy Felipe. estoy con un problema con mi calefont, dejo de funcionar hace un par de dias"}, "unknown", id="false-commune"),
        pytest.param("address", "Soy Braulio, me dieron este numero. tengo un problema con mi calefont. Necesito que lo vengan a ver.", {"address": "Soy Braulio, me dieron este numero. tengo un problema con mi calefont. Necesito que lo vengan a ver."}, None, id="whole-message-address"),
        pytest.param("consent", "dejo de prender hace un par de dias.", {}, None, id="non-allowlisted-consent"),
        pytest.param("failure", "quiero hacer mantencion de caldera", {"failure": "quiero hacer mantencion de caldera"}, None, id="intent-as-failure"),
    ],
)
def test_real_corruptions_are_not_accepted_as_answers(harness, field, turn, extracted, bad_value):
    initial = {"_pending": "consent" if field == "consent" else [field], "_asked": {field: 1}}
    result = capture_node.capture(make_state(turn, captured=initial, extracted=extracted))

    if bad_value == "unknown":
        assert result["captured"].get(field) == "unknown"
    else:
        assert field not in result["captured"]
        assert result["captured"]["_pending"] == ("consent" if field == "consent" else [field])
        assert turn not in " ".join(result.get("replies", []))


def test_email_requires_a_valid_email_and_only_pending_fields_merge(harness):
    result = capture_node.capture(make_state(
        "not an email", captured={"_pending": ["email"], "_asked": {"email": 1}},
        extracted={"email": "not an email", "name": "Felipe"},
    ))
    assert "email" not in result["captured"]
    assert "name" not in result["captured"]
    assert result["captured"]["_pending"] == ["email"]


def test_skip_unknown_path_still_advances(harness):
    result = capture_node.capture(make_state(
        "no se", captured={"_pending": ["failure"], "_asked": {"failure": 1}},
    ))
    assert result["captured"]["failure"] == "unknown"
    assert result["captured"]["_pending"] == ["equipment"]


def test_ack_uses_configured_text_and_only_non_sensitive_captured_facts(harness, monkeypatch):
    monkeypatch.setattr(capture_node, "get_capture_ack", lambda _session: "Gracias {{nombre}} por el dato de {{equipo}}.")
    result = capture_node.capture(make_state(
        "quiero una visita", captured={"name": "Ana", "equipment": "calefont", "email": "secret@example.cl", "address": "Privada 1"},
    ))
    reply = result["replies"][0]
    assert reply.startswith("Gracias Ana por el dato de calefont.")
    assert "secret@example.cl" not in reply and "Privada 1" not in reply


def test_preventive_request_skips_failure_and_marks_it(harness):
    result = capture_node.capture(make_state(
        "Quiero hacer MANTENCIÓN de caldera", captured={},
    ))
    assert result["captured"].get("failure") is None
    assert "failure" in result["captured"]["_skipped"]
    assert result["captured"]["_pending"] == ["equipment"]
    assert "qué pasa con el equipo" not in result["replies"][0].lower()


def test_ack_is_not_repeated_on_consecutive_questions(harness, monkeypatch):
    """S3: an acknowledgement marks a transition, it must not become a tic."""
    monkeypatch.setattr(capture_node, "get_capture_ack", lambda _session: "Gracias {{nombre}}. ")
    captured = {"failure": "no enciende", "equipment": "calefont", "name": "Ana"}

    first = capture_node.capture(make_state("hola", captured=dict(captured)))
    second = capture_node.capture(make_state("no se", captured=dict(first["captured"])))

    assert first["replies"][0].startswith("Gracias Ana.")
    assert not second["replies"][0].startswith("Gracias Ana.")


def test_ack_has_a_single_source_and_it_is_the_reply_catalog(monkeypatch):
    """S3: the panel's reply editor is the only place `capture_ack` is configured."""
    from app.services import settings as settings_module

    assert "capture.ack" not in settings_module.SETTINGS_DEFAULTS
    monkeypatch.setattr(
        settings_module,
        "get_setting",
        lambda _session, key, default=None: (
            {"capture_ack": "Listo {{nombre}}: "}
            if key == settings_module.REPLY_TEXTS_KEY
            else default
        ),
    )

    assert settings_module.get_capture_ack(object()) == "Listo {{nombre}}: "
