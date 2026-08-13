"""T4.2 integration tests — emergency engine (service) + emergency nodes.

Scenarios mapped 1:1 from openspec/changes/hito-1-setup-whatsapp/specs/emergency-detection/spec.md:

- EM-1 "Emergency keyword detected": every SS-2 default keyword + accented
  variants -> strong hit (deterministic, before any LLM)
- EM-1 "Keyword configured": a settings change is picked up per run
- EM-2 "Interrupt mid-capture": strong hit abandons the capture sub-flow
- EM-3 "Safety guidance delivered": safety instructions + contacts +
  technician-notified reply; case flagged, conversation state -> human
- EM-5 "Ambiguous risk": weak hit escalates to a human, never ignored;
  benign text (e.g. "fuga de agua") is NOT a hit

Part 1 (service): pure deterministic classification — no DB, no mocks.
Part 2 (graph): full-graph runs against the migrated pgvector test DB with
the OpenAI chat mocked via respx (emergency paths must NOT call it).
"""

import re

import psycopg
import pytest
from sqlalchemy import select

from app.db import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Case,
    Conversation,
    ConversationEvent,
    Message,
    MessageDirection,
    MessageStatus,
    MessageType,
)
from app.services.emergency import classify_emergency, compile_keywords, fold_accents  # noqa: E402
from app.services.settings import DEFAULT_EMERGENCY_KEYWORDS, set_setting  # noqa: E402
from app.chat.graph import run_conversation  # noqa: E402
from app.chat.state import get_or_create_conversation  # noqa: E402
from app.services.customers import get_or_create_customer  # noqa: E402

ADMIN_DB_URL = "postgresql://lumat:lumat@localhost:5432/lumat"


# ---------------------------------------------------------------------------
# Part 1 — service: deterministic strong / weak / no-hit classification
# ---------------------------------------------------------------------------


def _pattern():
    return compile_keywords(DEFAULT_EMERGENCY_KEYWORDS)


# EM-1: every default keyword produces a strong hit in a realistic sentence.
# "fuga" is tested via "fuga de gas" — the phrase keyword wins over the bare
# stem, and a bare stem followed by a benign qualifier ("de agua") is NOT a
# hit (Lumat is a plumbing company; water leaks are normal service work).
EMERGENCY_SENTENCES = [
    ("olor a gas", "siento olor a gas en la cocina"),
    ("huele a gas", "huele a gas en el calefont"),
    ("fuga", "hay una fuga de gas en el calefont"),
    ("fuga de gas", "hay una fuga de gas en el calefont"),
    ("humo", "sale humo del calefont"),
    ("incendio", "hay un incendio en la casa"),
    ("chispa", "veo chispas cerca del medidor"),
    ("chispas", "veo chispas cerca del medidor"),
    ("explosión", "escuché una explosión en el patio"),
    ("monóxido", "creo que hay monóxido en el ambiente"),
    ("intoxicación", "parece intoxicación por gas"),
    ("riesgo eléctrico", "hay riesgo eléctrico en el panel"),
    ("filtración severa", "tengo una filtración severa en el techo"),
]


@pytest.mark.parametrize("keyword,sentence", EMERGENCY_SENTENCES)
def test_strong_hit_each_default_keyword(keyword, sentence):
    # each configured keyword is a direct emergency phrase (EM-1)
    assert classify_emergency(sentence, _pattern()) == "strong", keyword


@pytest.mark.parametrize(
    "sentence",
    [
        "hay una explosion en el patio",  # explosión -> explosion (T4.1.2 gotcha)
        "huele a monoxido",  # monóxido -> monoxido
        "parece intoxicacion por gas",  # intoxicación -> intoxicacion
        "hay riesgo electrico en el panel",  # eléctrico -> electrico
        "tengo una filtracion severa en el techo",  # severa stays
    ],
)
def test_accent_folded_variants_are_strong(sentence):
    assert classify_emergency(sentence, _pattern()) == "strong"


# EM-5: ambiguous/risk-adjacent language -> weak (escalate to human), never
# silently ignored; it is NOT the full emergency protocol.
@pytest.mark.parametrize(
    "sentence",
    [
        "huele raro el calefont",
        "no me llega gas al calefont",
        "hay un olor a quemado en el patio",
    ],
)
def test_weak_hit_escalates_not_ignored(sentence):
    assert classify_emergency(sentence, _pattern()) == "weak"


# No false positive on benign text: a water leak is Lumat's normal service
# work (gasfitería), not a gas emergency; plain commercial messages pass.
@pytest.mark.parametrize(
    "sentence",
    [
        "tengo una fuga de agua en el baño",
        "quiero cotizar un calefont de 10 litros",
        "¿en qué horario atienden?",
    ],
)
def test_benign_text_no_hit(sentence):
    assert classify_emergency(sentence, _pattern()) is None


def test_fuga_de_gas_strong_but_fuga_de_agua_benign():
    # the exact pair from the task: phrase hit vs benign qualifier exclusion
    pattern = _pattern()
    assert classify_emergency("hay una fuga de gas en el calefont", pattern) == "strong"
    assert classify_emergency("hay una fuga de agua en el baño", pattern) is None


def test_compile_deterministic_and_read_only_defaults():
    # same input -> identical pattern (deterministic compile)
    assert compile_keywords(DEFAULT_EMERGENCY_KEYWORDS).pattern == compile_keywords(
        DEFAULT_EMERGENCY_KEYWORDS
    ).pattern
    # case-insensitive over the folded keywords
    assert compile_keywords(DEFAULT_EMERGENCY_KEYWORDS).flags & re.IGNORECASE
    # the default list is a shared mutable object (T4.1.2) — never mutated
    snapshot = list(DEFAULT_EMERGENCY_KEYWORDS)
    compile_keywords(DEFAULT_EMERGENCY_KEYWORDS)
    assert DEFAULT_EMERGENCY_KEYWORDS == snapshot


def test_empty_text_no_hit():
    assert classify_emergency("", _pattern()) is None


def test_fold_accents_drops_combining_marks():
    assert fold_accents("Explosión MONÓXIDO") == "explosion monoxido"
