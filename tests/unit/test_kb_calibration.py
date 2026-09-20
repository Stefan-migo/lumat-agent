"""Model-free contracts for the KB retrieval-calibration harness.

Why this file exists
--------------------
The calibration harness in `scripts/kb_calibration.py` loads the **real** embedding
model and is not deterministic, so it can never be part of this suite. What *is*
pinned here is everything that must not rot silently:

- the **corpus schema** (`scripts/kb_calibration_corpus.yaml`), so a fixture edit
  cannot break a label reference or invent a class unnoticed;
- the **scoring core** (threshold and rule evaluation), driven by synthetic score
  vectors whose expected answer is known by construction.

Nothing here touches the database, the network, or `fastembed`.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "tests"))

import kb_calibration as cal  # noqa: E402
import _testdb  # noqa: E402

CORPUS_PATH = REPO_ROOT / "scripts" / "kb_calibration_corpus.yaml"


# ---------------------------------------------------------------------------
# Corpus schema — the fixture is the instrument; a broken fixture is a silent
# wrong answer, which is worse than no benchmark.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def corpus():
    return cal.load_corpus(CORPUS_PATH)


def test_corpus_loads_and_ids_are_unique(corpus):
    doc_ids = [d.id for d in corpus.docs]
    query_ids = [q.id for q in corpus.queries]
    assert len(doc_ids) == len(set(doc_ids)), "duplicate document id"
    assert len(query_ids) == len(set(query_ids)), "duplicate query id"


def test_corpus_labels_resolve_to_declared_documents(corpus):
    declared = {d.id for d in corpus.docs}
    unresolved = {
        q.id: sorted(set(q.relevant_doc_ids) - declared)
        for q in corpus.queries
        if set(q.relevant_doc_ids) - declared
    }
    assert unresolved == {}, f"labels point at documents that do not exist: {unresolved}"


def test_corpus_uses_only_the_closed_class_set(corpus):
    assert {q.query_class for q in corpus.queries} <= cal.QUERY_CLASSES
    assert {d.visibility for d in corpus.docs} <= cal.VISIBILITIES


def test_out_of_domain_queries_declare_no_relevant_documents(corpus):
    wrong = [q.id for q in corpus.queries if q.query_class == "out_of_domain" and q.relevant_doc_ids]
    assert wrong == [], f"out_of_domain queries must not point at a document: {wrong}"


def test_answerable_queries_declare_at_least_one_relevant_document(corpus):
    wrong = [
        q.id for q in corpus.queries if q.query_class == "answerable" and not q.relevant_doc_ids
    ]
    assert wrong == [], f"answerable queries need a relevant document: {wrong}"


def test_corpus_covers_every_document_class_from_the_client_request(corpus):
    """Topology mirrors docs/solicitud-al-cliente-lumat.md:204-214 (D2)."""
    classes = {d.doc_class for d in corpus.docs}
    assert classes == cal.DOCUMENT_CLASSES, f"uncovered/missing classes: {cal.DOCUMENT_CLASSES - classes}"


def test_corpus_has_enough_volume_to_separate_two_distributions(corpus):
    by_class = {}
    for q in corpus.queries:
        by_class[q.query_class] = by_class.get(q.query_class, 0) + 1
    assert len(corpus.docs) >= 20, "a benchmark this small measures nothing"
    assert len(corpus.queries) >= 40
    for name, minimum in (("answerable", 15), ("out_of_domain", 8), ("near_miss", 8)):
        assert by_class.get(name, 0) >= minimum, f"too few {name} queries: {by_class}"


def test_corpus_includes_customer_documents_for_the_customer_run(corpus):
    assert sum(1 for d in corpus.docs if d.visibility == "customer") >= 15


def test_corpus_makes_the_audience_filter_observable(corpus):
    """D6: an internal-only answer must be reachable unscoped and hidden as customer.

    Without this, a later "threshold fix" could actually be papering over a broken
    audience filter, and the matrix would not show it.
    """
    internal_docs = {d.id for d in corpus.docs if d.visibility == "internal"}
    assert internal_docs, "no internal document: the audience axis is untested"

    internal_only = [q for q in corpus.queries if q.visible_to == "internal"]
    assert internal_only, "no internal_only query: the filter's effect is unobservable"
    for q in internal_only:
        assert q.query_class == "answerable"
        assert set(q.relevant_doc_ids) <= internal_docs, (
            f"{q.id}: an internal_only query must be answered only by internal documents"
        )


def _database_url(port, database="lumat"):
    return f"postgresql+psycopg://app:app@localhost:{port}/{database}"


def test_environment_refuses_missing_test_admin_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _database_url(_testdb.host_port()))
    monkeypatch.delenv("TEST_ADMIN_DB_URL", raising=False)

    with pytest.raises(SystemExit):
        cal._ensure_environment()


def test_environment_refuses_non_local_database_host(monkeypatch):
    url = f"postgresql+psycopg://app:app@db:{_testdb.host_port()}/lumat"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("TEST_ADMIN_DB_URL", url)

    with pytest.raises(SystemExit):
        cal._ensure_environment()


def test_environment_refuses_different_database_ports(monkeypatch):
    port = _testdb.host_port()
    monkeypatch.setenv("DATABASE_URL", _database_url(port))
    monkeypatch.setenv("TEST_ADMIN_DB_URL", _database_url(port + 1))

    with pytest.raises(SystemExit):
        cal._ensure_environment()


def test_environment_refuses_different_database_names(monkeypatch):
    port = _testdb.host_port()
    monkeypatch.setenv("DATABASE_URL", _database_url(port, "lumat"))
    monkeypatch.setenv("TEST_ADMIN_DB_URL", _database_url(port, "other"))

    with pytest.raises(SystemExit):
        cal._ensure_environment()


def test_environment_refuses_a_port_not_derived_for_this_worktree(monkeypatch):
    port = _testdb.host_port()
    url = _database_url(port + 1)
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("TEST_ADMIN_DB_URL", url)

    with pytest.raises(SystemExit):
        cal._ensure_environment()


def test_environment_accepts_the_matching_derived_test_database(monkeypatch):
    url = _database_url(_testdb.host_port())
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("TEST_ADMIN_DB_URL", url)

    cal._ensure_environment()


def test_load_corpus_rejects_an_unknown_class(tmp_path):
    bad = tmp_path / "corpus.yaml"
    bad.write_text(
        "documents:\n"
        "  - {id: d1, title: T, doc_class: faq, visibility: customer, content: hola}\n"
        "queries:\n"
        "  - {id: q1, text: hola, class: nonsense, relevant_doc_ids: [d1]}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="nonsense"):
        cal.load_corpus(bad)


def test_load_corpus_rejects_a_dangling_label(tmp_path):
    bad = tmp_path / "corpus.yaml"
    bad.write_text(
        "documents:\n"
        "  - {id: d1, title: T, doc_class: faq, visibility: customer, content: hola}\n"
        "queries:\n"
        "  - {id: q1, text: hola, class: answerable, relevant_doc_ids: [ghost]}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="ghost"):
        cal.load_corpus(bad)


# ---------------------------------------------------------------------------
# Ingested-text axis — the title-in-embedding experiment.
# ---------------------------------------------------------------------------


def test_index_text_leaves_the_body_alone_when_the_axis_is_off():
    doc = cal.CalibrationDoc(
        id="d1",
        title="Plazos de respuesta",
        doc_class="procedimientos",
        visibility="customer",
        content="Respondemos los mensajes dentro de 24 horas habiles.",
    )
    assert cal.index_text(doc, index_title=False) == doc.content


def test_index_text_prepends_the_title_as_its_own_block_when_the_axis_is_on():
    doc = cal.CalibrationDoc(
        id="d1",
        title="Plazos de respuesta",
        doc_class="procedimientos",
        visibility="customer",
        content="Respondemos los mensajes dentro de 24 horas habiles.",
    )
    text = cal.index_text(doc, index_title=True)
    # A blank line, not a bare prefix: the splitter then keeps the title and the
    # first paragraph from being fused into one sentence.
    assert text == f"{doc.title}\n\n{doc.content}"
    assert doc.content in text


# ---------------------------------------------------------------------------
# Scoring core — accept predicates. Synthetic scores, known expected answer.
# ---------------------------------------------------------------------------


def test_accept_absolute_is_inclusive_at_the_threshold():
    scores = (("d1", 0.65),)
    assert cal.accept_absolute(scores, 0.65) is True
    assert cal.accept_absolute(scores, 0.66) is False
    assert cal.accept_absolute((), 0.0) is False


def test_accept_margin_needs_a_floor_and_a_gap():
    close = (("d1", 0.70), ("d2", 0.69))
    far = (("d1", 0.70), ("d2", 0.10))
    assert cal.accept_margin(close, floor=0.30, margin=0.05) is False
    assert cal.accept_margin(far, floor=0.30, margin=0.05) is True
    # A floor still applies: a dominant but weak top-1 is declined.
    assert cal.accept_margin((("d1", 0.20), ("d2", 0.01)), floor=0.30, margin=0.05) is False


def test_accept_margin_handles_a_single_result():
    """One chunk cannot show dominance, so only the floor can decide."""
    assert cal.accept_margin((("d1", 0.50),), floor=0.30, margin=0.05) is True
    assert cal.accept_margin((("d1", 0.10),), floor=0.30, margin=0.05) is False


def test_accept_relative_needs_a_dominant_top1_over_the_mean():
    flat = (("d1", 0.60), ("d2", 0.58), ("d3", 0.57))  # mean ~0.583, ratio ~1.03
    peaked = (("d1", 0.60), ("d2", 0.20), ("d3", 0.15))  # mean ~0.317, ratio ~1.9
    assert cal.accept_relative(flat, floor=0.30, ratio=1.25) is False
    assert cal.accept_relative(peaked, floor=0.30, ratio=1.25) is True


# ---------------------------------------------------------------------------
# Scoring core — outcome accounting.
# ---------------------------------------------------------------------------


def _outcome(qid, klass, should_hit, relevant, scores):
    return cal.QueryOutcome(
        query_id=qid,
        query_class=klass,
        should_hit=should_hit,
        relevant_doc_ids=frozenset(relevant),
        scores=tuple(scores),
    )


def test_metrics_separate_declining_correctly_from_grounding_wrongly():
    outcomes = [
        # answerable, relevant chunk accepted -> good answer
        _outcome("a1", "answerable", True, ["d1"], [("d1", 0.70)]),
        # answerable, accepted but off-target -> false grounding, not a recall win
        _outcome("a2", "answerable", True, ["d2"], [("d9", 0.80)]),
        # answerable, nothing passes -> a wrong refusal
        _outcome("a3", "answerable", True, ["d3"], [("d3", 0.10)]),
        # unanswerable, correctly refused
        _outcome("u1", "out_of_domain", False, [], [("d9", 0.20)]),
        # unanswerable, accepted -> false accept
        _outcome("u2", "near_miss", False, [], [("d9", 0.90)]),
    ]
    m = cal.metrics_at(outcomes, accept=lambda scores: cal.accept_absolute(scores, 0.50))
    assert m["answerable_total"] == 3
    assert m["answerable_grounded"] == 1
    assert m["answerable_false_grounded"] == 1
    assert m["answerable_declined"] == 1
    assert m["unanswerable_total"] == 2
    assert m["unanswerable_false_accept"] == 1
    assert m["answerable_recall"] == pytest.approx(1 / 3)
    assert m["unanswerable_false_accept_rate"] == pytest.approx(0.5)
    # balanced accuracy = (recall + specificity) / 2
    assert m["balanced_accuracy"] == pytest.approx((1 / 3 + 0.5) / 2)


def test_sweep_absolute_finds_the_threshold_that_separates_the_classes():
    outcomes = [
        _outcome("a1", "answerable", True, ["d1"], [("d1", 0.50)]),
        _outcome("a2", "answerable", True, ["d2"], [("d2", 0.60)]),
        _outcome("u1", "out_of_domain", False, [], [("d9", 0.20)]),
        _outcome("u2", "near_miss", False, [], [("d9", 0.30)]),
    ]
    points = cal.sweep_absolute(outcomes, thresholds=[0.2, 0.4, 0.55, 0.7])
    best = max(points, key=lambda p: (p["balanced_accuracy"], -p["threshold"]))
    assert best["threshold"] == 0.4  # 0.2 accepts the unanswerable, 0.55 drops a1
    assert best["balanced_accuracy"] == pytest.approx(1.0)
    at_020 = next(p for p in points if p["threshold"] == 0.2)
    assert at_020["unanswerable_false_accept"] == 2


def test_report_includes_the_top_irrelevant_score():
    """The number that bounds any absolute threshold from below."""
    outcomes = [
        _outcome("a1", "answerable", True, ["d1"], [("d1", 0.62)]),
        _outcome("u1", "out_of_domain", False, [], [("d9", 0.19)]),
        _outcome("u2", "near_miss", False, [], [("d9", 0.41)]),
    ]
    report = cal.summarize(outcomes)
    assert report["top_irrelevant_score"] == pytest.approx(0.41)
    assert report["lowest_answerable_top1"] == pytest.approx(0.62)
    assert report["separation_margin"] == pytest.approx(0.62 - 0.41)


def test_summarize_reports_the_overlap_when_no_threshold_separates():
    """Overlap is the finding, not a failure: it is what forces a different rule."""
    outcomes = [
        _outcome("a1", "answerable", True, ["d1"], [("d1", 0.45)]),
        _outcome("u1", "near_miss", False, [], [("d9", 0.50)]),
    ]
    report = cal.summarize(outcomes)
    assert report["separation_margin"] < 0
    assert report["best_absolute"]["balanced_accuracy"] < 1.0


def test_compare_rules_picks_each_shape_best_configuration():
    outcomes = [
        _outcome("a1", "answerable", True, ["d1"], [("d1", 0.62), ("d9", 0.20)]),
        _outcome("a2", "answerable", True, ["d2"], [("d2", 0.55), ("d9", 0.10)]),
        _outcome("u1", "near_miss", False, [], [("d9", 0.55), ("d8", 0.54)]),
        _outcome("u2", "out_of_domain", False, [], [("d9", 0.30)]),
    ]
    comparison = cal.compare_rules(outcomes)
    assert set(comparison) == {"absolute", "margin", "relative"}
    # The near_miss pair (0.55 vs 0.54) sits inside the answerable band; only a
    # rule that reads the gap can decline it while keeping both answerables.
    assert comparison["margin"]["balanced_accuracy"] == pytest.approx(1.0)
    assert comparison["absolute"]["balanced_accuracy"] < 1.0
