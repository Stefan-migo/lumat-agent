"""Model-free contracts for the KB answer-fidelity harness.

Why this file exists
--------------------
`scripts/kb_fidelity.py` drives the **real** conversation graph against the **real**
provider, so it is neither deterministic nor free and can never be part of this
suite. What *is* pinned here is the scoring core, and every assertion below has an
expected answer fixed by construction rather than by a recorded run:

- `ungrounded_numbers` — the deterministic triage core. A wrong normalization
  either reports a faithful answer as invented, or hides an invented price. Both
  failures are silent, which is why they are pinned.
- `classify_outcome` — the CM-4 / handoff / clarification surface, including the
  CM-1 greeting that the reply accumulator merges into the same list.
- `summarize` — the per-class rates the report is read from.

Nothing here touches the database, the network, or `fastembed`.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import kb_fidelity as fid  # noqa: E402

from app.chat.nodes import respond as _respond  # noqa: E402
from app.chat.state import ConversationState  # noqa: E402


# ---------------------------------------------------------------------------
# Number normalization — the load-bearing half of the triage core
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Chilean thousands separators group by three, so they are separators.
        ("45.000", "45000"),
        ("52.000", "52000"),
        ("1.234.567", "1234567"),
        ("45.000", "45000"),
        # A separator that does NOT group by three is a decimal mark. The
        # fraction is dropped on purpose: the check compares magnitudes, and
        # `1,5` vs `1.5` must not become `15` vs `15`.
        ("1,5", "1"),
        ("0,5", "0"),
        # No separator at all.
        ("45000", "45000"),
        ("12", "12"),
        # Leading zeros collapse, so "045" and "45" are the same magnitude.
        ("045", "45"),
    ],
)
def test_normalize_number(raw, expected):
    assert fid.normalize_number(raw) == expected


def test_extract_numbers_finds_and_normalizes_every_token():
    found = fid.extract_numbers(
        "Mantención de calefón: 45.000 pesos. Caldera: 60.000. Plazo: 48 horas."
    )
    assert found == {"45000", "60000", "48"}


def test_extract_numbers_returns_empty_for_text_without_digits():
    assert fid.extract_numbers("No hay valores en este texto.") == set()


# ---------------------------------------------------------------------------
# ungrounded_numbers — flags, never verdicts
# ---------------------------------------------------------------------------


def test_grounded_number_is_not_flagged():
    """The chunk states the price the reply states, in the same notation."""
    flagged = fid.ungrounded_numbers(
        "La mantención de calefón cuesta 45.000 pesos.",
        ["Mantención de calefón: 45.000 pesos, incluye limpieza del quemador."],
    )
    assert flagged == []


def test_notation_difference_alone_is_not_flagged():
    """Same magnitude, different separator convention, on either side."""
    assert fid.ungrounded_numbers("cuesta 45.000", ["cuesta 45000"]) == []
    assert fid.ungrounded_numbers("cuesta 45000", ["cuesta 45.000"]) == []


def test_invented_price_is_flagged():
    """The reply states a price no chunk contains. This is the failure class."""
    flagged = fid.ungrounded_numbers(
        "La mantención de calefón cuesta 52.000 pesos.",
        ["Mantención de calefón: 45.000 pesos, incluye limpieza del quemador."],
    )
    assert flagged == ["52000"]


def test_a_number_absent_from_every_chunk_is_flagged_across_the_whole_set():
    """Grounding is against the full retrieved set, not one chunk."""
    flagged = fid.ungrounded_numbers(
        "La caldera cuesta 60.000 y el calefón 45.000.",
        [
            "Mantención de calefón: 45.000 pesos.",
            "Mantención de caldera: 60.000 pesos.",
        ],
    )
    assert flagged == []


def test_faithful_reply_may_still_introduce_a_number_and_is_flagged():
    """HONEST FRAMING, pinned so nobody reads the flag as a verdict.

    A reply that is perfectly faithful can introduce a number the chunk does not
    contain (a count, a date, a phone). The harness reports it; a human decides.
    """
    flagged = fid.ungrounded_numbers(
        "Atendemos en 12 comunas de la zona.",
        ["Cobertura: comunas de la Región Metropolitana."],
    )
    assert flagged == ["12"]


def test_reply_without_numbers_is_never_flagged():
    assert fid.ungrounded_numbers("No puedo responder con seguridad a eso.", []) == []


def test_no_chunks_means_every_number_in_the_reply_is_ungrounded():
    """A reply with no retrieved chunk behind it has no grounding at all."""
    flagged = fid.ungrounded_numbers("El valor es 45.000 pesos.", [])
    assert flagged == ["45000"]


# ---------------------------------------------------------------------------
# classify_outcome — CM-4 / handoff / clarification, greeting-aware
# ---------------------------------------------------------------------------


def test_answered_is_the_fallback_for_free_text():
    assert fid.classify_outcome(["La mantención cuesta 45.000 pesos."]) == "answered"


def test_cannot_answer_reply_is_a_decline():
    assert fid.classify_outcome([fid.CANNOT_ANSWER_REPLY]) == "declined"


def test_handoff_reply_is_a_handoff():
    assert fid.classify_outcome([fid.HANDOFF_REPLY]) == "handed_off"


def test_clarification_reply_is_a_clarification():
    assert fid.classify_outcome([fid.CLARIFICATION_REPLY]) == "clarified"


def test_cm1_greeting_is_stripped_before_classifying():
    """The accumulator merges the greeting and the terminal reply (D10)."""
    replies = [fid.greeting(), fid.CANNOT_ANSWER_REPLY]
    assert fid.classify_outcome(replies) == "declined"


def test_cm1_greeting_fused_with_the_answer_is_stripped_before_classifying():
    """First turn: the greeting and the answer travel in ONE message (CM-1)."""
    fused = f"{fid.greeting()}\n\n{fid.CANNOT_ANSWER_REPLY}"
    assert fid.classify_outcome([fused]) == "declined"
    assert fid.greeting_emitted([fused]) is True


def test_cm1_short_greeting_fused_with_the_answer_is_stripped_too():
    """A first turn that states the need gets the short greeting, also fused."""
    fused = f"{fid.GREETING_SHORT_HEADER}\n\n{fid.CANNOT_ANSWER_REPLY}"
    assert fid.classify_outcome([fused]) == "declined"
    assert fid.greeting_emitted([fused]) is True


def test_greeting_alone_is_not_an_answer():
    """A turn that only greeted produced no outcome to score.

    It is reported as its own outcome rather than as `other`: on first contact the
    CM-1 open greeting IS the reply, and `respond` stays silent when classification is skipped
    not place the message. That is correct behaviour, not a missing outcome.
    """
    assert fid.classify_outcome([fid.greeting()]) == "greeted_only"


def test_capture_prompt_is_not_an_answer():
    """The CM-2 capture flow asks for a field; that is not an answer to the query.

    Four `near_miss` queries came back as "¿Cuál es tu nombre?" in the first full
    run. Scored as `answered`, they would have read as fabricated answers.
    """
    assert fid.classify_outcome(["¿Cuál es tu nombre?"]) == "capture_started"
    assert fid.classify_outcome([fid.greeting(), "¿En qué comuna te encuentras?"]) == (
        "capture_started"
    )
    assert fid.classify_outcome([fid.COMPLETION_REPLY]) == "capture_started"


def test_emergency_protocol_is_read_from_the_event_not_the_reply_text():
    """The EM-3 safety replies are free text from panel-editable settings.

    Scoring them by reply shape made the two gas-emergency queries the only
    `answered` rows in the first full run — reporting two KB answers where the KB
    was never consulted.
    """
    events = [{"event": "emergency", "cause": "strong_hit"}]
    assert fid.classify_outcome(["INSTRUCCIONES DE SEGURIDAD:\n- Corta el suministro."], events) == (
        "emergency_protocol"
    )
    # The same reply with no emergency event is a plain answer.
    assert fid.classify_outcome(["INSTRUCCIONES DE SEGURIDAD:\n- Corta el suministro."]) == (
        "answered"
    )


def test_empty_replies_is_other():
    assert fid.classify_outcome([]) == "other"


def test_greeting_emitted_is_reported_separately():
    assert fid.greeting_emitted([fid.greeting(), "hola"]) is True
    assert fid.greeting_emitted(["hola"]) is False
    assert fid.greeting_emitted([]) is False


# ---------------------------------------------------------------------------
# summarize — the per-class rates the report is read from
# ---------------------------------------------------------------------------

_ROWS = [
    {"class": "answerable", "outcome": "answered", "ungrounded": []},
    {"class": "answerable", "outcome": "answered", "ungrounded": ["52000"]},
    {"class": "answerable", "outcome": "declined", "ungrounded": []},
    {"class": "near_miss", "outcome": "handed_off", "ungrounded": []},
    {"class": "near_miss", "outcome": "answered", "ungrounded": []},
    {"class": "out_of_domain", "outcome": "declined", "ungrounded": []},
]


def test_summarize_totals():
    assert fid.summarize(_ROWS)["total"] == 6


def test_summarize_answerable_class():
    row = fid.summarize(_ROWS)["by_class"]["answerable"]
    assert row["n"] == 3
    assert row["answered"] == 2
    assert row["declined"] == 1
    assert row["answered_rate"] == pytest.approx(2 / 3)
    assert row["non_answer_rate"] == pytest.approx(1 / 3)
    assert row["ungrounded_flag_count"] == 1
    assert row["ungrounded_flag_rate"] == pytest.approx(1 / 3)


def test_summarize_non_answerable_classes_report_non_answer_rate():
    """For these classes the correct behaviour is NOT answering."""
    by_class = fid.summarize(_ROWS)["by_class"]
    assert by_class["near_miss"]["non_answer_rate"] == pytest.approx(0.5)
    assert by_class["out_of_domain"]["non_answer_rate"] == pytest.approx(1.0)


def test_summarize_always_carries_the_three_label_classes():
    """A class absent from the run must read as n=0, not as missing."""
    summary = fid.summarize([])
    assert summary["total"] == 0
    assert set(summary["by_class"]) == {"answerable", "near_miss", "out_of_domain"}
    for row in summary["by_class"].values():
        assert row["n"] == 0
        assert row["answered_rate"] == 0.0
        assert row["non_answer_rate"] == 0.0
        assert row["ungrounded_flag_rate"] == 0.0


def test_summarize_counts_every_outcome_kind():
    rows = [
        {"class": "answerable", "outcome": kind, "ungrounded": []}
        for kind in fid.OUTCOMES
    ]
    row = fid.summarize(rows)["by_class"]["answerable"]
    assert row["n"] == len(fid.OUTCOMES)
    for kind in fid.OUTCOMES:
        assert row[kind] == 1
    # Exactly one of the seven outcomes is a free-text answer.
    assert row["answered_rate"] == pytest.approx(1 / len(fid.OUTCOMES))
    assert row["non_answer_rate"] == pytest.approx((len(fid.OUTCOMES) - 1) / len(fid.OUTCOMES))


def test_summarize_separates_handoffs_by_layer():
    """A KB miss and a safety-gate handoff must never be counted as the same thing.

    `emergency_weak_hit` fires before retrieval runs, so reading it as a KB
    failure would blame the KB for a verdict it never made.
    """
    rows = [
        {"class": "answerable", "outcome": "handed_off", "ungrounded": [],
         "escalate_reason": "kb_miss"},
        {"class": "answerable", "outcome": "handed_off", "ungrounded": [],
         "escalate_reason": "kb_miss"},
        {"class": "answerable", "outcome": "handed_off", "ungrounded": [],
         "escalate_reason": "emergency_weak_hit"},
        {"class": "answerable", "outcome": "answered", "ungrounded": []},
    ]
    assert fid.summarize(rows)["handoff_reasons"] == {
        "kb_miss": 2,
        "emergency_weak_hit": 1,
    }


def test_summarize_handoff_reasons_is_empty_without_escalations():
    assert fid.summarize(_ROWS)["handoff_reasons"] == {}


# ---------------------------------------------------------------------------
# Retrieval fidelity — the instrument must measure the call production makes
# ---------------------------------------------------------------------------

RAW = "me dieron tu contacto para una mantencion de caldera"
SERVICE = "mantención de caldera"
CHUNK = {
    "document_id": 1,
    "version": 1,
    "chunk_index": 1,
    "content": "Mantención de caldera: inspección, limpieza y purgado.",
    "source_meta": None,
    "similarity": 0.61,
}


def _recording_retrieve(monkeypatch, hit: str) -> list[tuple[str, dict]]:
    """Record every retrieval call; only the `hit` query returns a chunk."""
    calls: list[tuple[str, dict]] = []

    def fake_retrieve(session, query, **kwargs):
        calls.append((query, kwargs))
        return [CHUNK] if query == hit else []

    monkeypatch.setattr(_respond.kb, "retrieve", fake_retrieve)
    return calls


def test_the_instrument_makes_the_retrieval_production_makes(monkeypatch):
    """H01: `_retrieved_chunks` used to re-declare the call and drift from it.

    Two drifts were measured: no `global_only` (so project documents entered the
    chunk set production never saw) and no `service` fallback (so a miss caused
    by polite filler was reported as a KB failure production had rescued). Both
    are pinned here as one contract: same queries, same arguments.
    """
    calls = _recording_retrieve(monkeypatch, hit=SERVICE)
    state = ConversationState(
        customer_id=1,
        conversation_id=1,
        phone="+56900000000",
        intent="consulta",
        case={"service": SERVICE},
        window=[{"id": 1, "text": RAW}],
    )

    production = _respond.retrieve_chunks(None, state)
    production_calls = list(calls)
    calls.clear()
    instrument = fid._retrieved_chunks(None, RAW, intent="consulta", service=SERVICE)

    assert instrument == production
    assert calls == production_calls
    assert [query for query, _ in calls] == [RAW, SERVICE]
    assert all(kwargs["global_only"] is True for _, kwargs in calls)
