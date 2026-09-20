"""KB retrieval-calibration harness (ODD: kb-retrieval-calibration).

Why this exists
---------------
`min_sim=0.65` (`app/services/kb.py:40`) declines questions the KB can answer. The
only previous evidence was four hand-run queries against a three-line document —
a signal, not a benchmark. Deciding what threshold (or which *shape* of rule) to
use needs a labeled corpus and the score distribution of relevant vs. irrelevant
queries, measured with the real model.

This harness is that instrument. It is deliberately NOT part of `pytest tests/`:
it loads the real ~130MB model and is not deterministic. The model-free half of
its contract (corpus schema + scoring math) IS suite-covered, in
`tests/unit/test_kb_calibration.py`.

How it measures (the design that matters)
-----------------------------------------
For every query it calls the **real** `kb.retrieve` once, with
`min_sim=FULL_RANKING_MIN_SIM` and a large `top_k`, so the single call returns the
**complete ranked score list**. Every threshold and every rule shape is then
scored offline from those numbers.

That is the deliberate answer to how this was being done before: moving `min_sim`
by hand against `GET /panel/api/kb/search`, an endpoint that accepts `top_k` and
`min_sim` **without range validation** (review advisory R3-001). Here the
parameter is never moved by hand, and `-1.0` is used rather than `0.0` so the
negative-cosine tail is not silently truncated by the `distance <= 1 - min_sim`
filter — a low-threshold false-accept analysis needs that tail.

Two audience modes are measured (`audience=None` and `audience="customer"`) so
"the model scores badly" can be told apart from "the audience filter hides the
right document". See `odd/tasks/kb-retrieval-calibration.md` (D4, D5, D6).

Usage
-----
    eval "$(bash infra/test-db.sh env)"          # required, see the ODD record
    uv run python scripts/kb_calibration.py
    uv run python scripts/kb_calibration.py --json /tmp/kb-calibration.json

Real-model notes
----------------
`fastembed` resolves the configured model id to a **quantized** ONNX build
(`qdrant/paraphrase-multilingual-MiniLM-L12-v2-onnx-Q`). The report records the
resolved source, because an absolute threshold is only meaningful for the build
it was measured on.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import urlparse

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

CORPUS_PATH = Path(__file__).with_name("kb_calibration_corpus.yaml")

# `app.config.Settings` requires the channel secrets even for a read-only KB run.
# These are placeholders for local measurement only, and `setdefault` means a real
# value in the environment always wins.
PLACEHOLDER_SETTINGS = {
    "APP_SECRET": "kb-calibration",
    "VERIFY_TOKEN": "kb-calibration",
    "META_ACCESS_TOKEN": "kb-calibration",
    "META_PHONE_NUMBER_ID": "0",
    "PANEL_SESSION_SECRET": "kb-calibration",
    "DEEPSEEK_API_KEY": "kb-calibration",
    "LANGCHAIN_TRACING_V2": "false",
    "LANGCHAIN_TRACING": "false",
}
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}

# Full ranking, not a filtered one: -1.0 => `distance <= 2.0` => every row.
FULL_RANKING_MIN_SIM = -1.0
FULL_RANKING_TOP_K = 500

VISIBILITIES = frozenset({"customer", "internal"})
QUERY_CLASSES = frozenset({"answerable", "out_of_domain", "near_miss"})
DOCUMENT_CLASSES = frozenset(
    {
        "catalogo_servicios",
        "tarifas",
        "comunas",
        "garantias",
        "procedimientos",
        "faq",
        "emergencias",
        "horarios",
        "tono",
        "mensajes_estandar",
    }
)

TITLE_PREFIX = "[calibration] "

Scores = Sequence[tuple[str, float]]
OutcomeMap = Callable[[Scores], bool]


# ---------------------------------------------------------------------------
# Corpus (pure) — the fixture is the instrument
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CalibrationDoc:
    id: str
    title: str
    doc_class: str
    visibility: str
    content: str


@dataclass(frozen=True)
class CalibrationQuery:
    id: str
    text: str
    query_class: str
    relevant_doc_ids: tuple[str, ...]
    visible_to: str = "customer"


@dataclass(frozen=True)
class Corpus:
    docs: tuple[CalibrationDoc, ...]
    queries: tuple[CalibrationQuery, ...]


def index_text(doc: CalibrationDoc, index_title: bool) -> str:
    """The text that actually gets chunked and embedded for one document.

    The experiment this exists for: `_store_chunks` embeds `chunk_text(doc.content)`
    only (`app/services/kb.py:159`), so a document's title never reaches the vector
    even though real customers phrase questions like titles. Passing
    `index_title=True` prepends the title as its own block — one blank line, so the
    splitter does not fuse it into the first sentence.

    The shape matches the one-line production fix (`chunk_text(f"{title}\\n\\n{content}")`),
    which puts the title in the first chunk. It is a measurement axis, not a
    production change: nothing outside this harness is touched.
    """
    if not index_title:
        return doc.content
    return f"{doc.title}\n\n{doc.content}"


def load_corpus(path: Path | str = CORPUS_PATH) -> Corpus:
    """Read and validate the labeled corpus. Raises ValueError on any violation."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}

    docs: list[CalibrationDoc] = []
    for entry in raw.get("documents") or []:
        doc = CalibrationDoc(
            id=str(entry["id"]),
            title=str(entry["title"]),
            doc_class=str(entry["doc_class"]),
            visibility=str(entry["visibility"]),
            content=str(entry["content"]),
        )
        if doc.doc_class not in DOCUMENT_CLASSES:
            raise ValueError(f"document {doc.id}: unknown doc_class {doc.doc_class!r}")
        if doc.visibility not in VISIBILITIES:
            raise ValueError(f"document {doc.id}: unknown visibility {doc.visibility!r}")
        docs.append(doc)

    duplicates = {d.id for d in docs if [x.id for x in docs].count(d.id) > 1}
    if duplicates:
        raise ValueError(f"duplicate document ids: {sorted(duplicates)}")

    declared = {d.id for d in docs}
    queries: list[CalibrationQuery] = []
    for entry in raw.get("queries") or []:
        klass = str(entry["class"])
        if klass not in QUERY_CLASSES:
            raise ValueError(f"query {entry['id']}: unknown class {klass!r}")
        query = CalibrationQuery(
            id=str(entry["id"]),
            text=str(entry["text"]),
            query_class=klass,
            relevant_doc_ids=tuple(str(x) for x in (entry.get("relevant_doc_ids") or [])),
            visible_to=str(entry.get("visible_to", "customer")),
        )
        if query.visible_to not in VISIBILITIES:
            raise ValueError(f"query {query.id}: unknown visible_to {query.visible_to!r}")
        dangling = set(query.relevant_doc_ids) - declared
        if dangling:
            raise ValueError(
                f"query {query.id}: labels point at undeclared document(s) {sorted(dangling)}"
            )
        if query.query_class == "answerable" and not query.relevant_doc_ids:
            raise ValueError(f"query {query.id}: answerable with no relevant document")
        if query.query_class != "answerable" and query.relevant_doc_ids:
            raise ValueError(f"query {query.id}: {query.query_class} must declare no document")
        queries.append(query)

    duplicate_queries = {q.id for q in queries if [x.id for x in queries].count(q.id) > 1}
    if duplicate_queries:
        raise ValueError(f"duplicate query ids: {sorted(duplicate_queries)}")

    return Corpus(docs=tuple(docs), queries=tuple(queries))


# ---------------------------------------------------------------------------
# Scoring core (pure) — accept predicates, one per rule shape
# ---------------------------------------------------------------------------


def accept_absolute(scores: Scores, threshold: float) -> bool:
    """Today's rule: any chunk at or above an absolute similarity."""
    return any(score >= threshold for _, score in scores)


def accept_margin(scores: Scores, floor: float, margin: float) -> bool:
    """A floor plus a gap between the best and the second-best chunk.

    A single retrieved chunk cannot demonstrate dominance, so only the floor
    decides. This is the shape that can decline a flat near-miss pair whose
    top-1 clears an absolute threshold.
    """
    if not scores:
        return False
    top1 = scores[0][1]
    if top1 < floor:
        return False
    if len(scores) < 2:
        return True
    return top1 - scores[1][1] >= margin


def accept_relative(scores: Scores, floor: float, ratio: float) -> bool:
    """A floor plus the best chunk standing out from the mean of the ranking."""
    if not scores:
        return False
    top1 = scores[0][1]
    if top1 < floor:
        return False
    mean = sum(score for _, score in scores) / len(scores)
    if mean <= 0:
        return top1 >= floor
    return top1 >= ratio * mean


# ---------------------------------------------------------------------------
# Scoring core (pure) — accounting
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QueryOutcome:
    """One query, already resolved for one audience mode.

    `should_hit` is resolved by the caller because it depends on the audience
    mode (an internal-only answer must MISS as customer and HIT unscoped).
    `scores` is the full ranking: (corpus document id, similarity), best first.
    """

    query_id: str
    query_class: str
    should_hit: bool
    relevant_doc_ids: frozenset[str]
    scores: tuple[tuple[str, float], ...]


def metrics_at(outcomes: Sequence[QueryOutcome], accept: OutcomeMap, floor: float | None = None) -> dict:
    """Score one acceptance rule over every outcome.

    `accept` is the query-level decision (the rule). `floor` is the per-chunk
    gate the rule implies for the *result set*: grounding asks whether the right
    document was among the chunks actually returned, not merely present in the
    ranking. For a plain absolute rule the floor is the threshold itself.
    """
    answerable_total = answerable_grounded = answerable_false_grounded = answerable_declined = 0
    unanswerable_total = unanswerable_false_accept = 0

    for outcome in outcomes:
        effective = (
            outcome.scores
            if floor is None
            else tuple((d, s) for d, s in outcome.scores if s >= floor)
        )
        accepted = accept(outcome.scores)
        grounded = accepted and any(d in outcome.relevant_doc_ids for d, _ in effective)

        if outcome.should_hit:
            answerable_total += 1
            if not accepted:
                answerable_declined += 1
            elif grounded:
                answerable_grounded += 1
            else:
                answerable_false_grounded += 1
        else:
            unanswerable_total += 1
            if accepted:
                unanswerable_false_accept += 1

    recall = answerable_grounded / answerable_total if answerable_total else 0.0
    false_accept = unanswerable_false_accept / unanswerable_total if unanswerable_total else 0.0
    return {
        "answerable_total": answerable_total,
        "answerable_grounded": answerable_grounded,
        "answerable_false_grounded": answerable_false_grounded,
        "answerable_declined": answerable_declined,
        "unanswerable_total": unanswerable_total,
        "unanswerable_false_accept": unanswerable_false_accept,
        "answerable_recall": recall,
        "unanswerable_false_accept_rate": false_accept,
        "balanced_accuracy": (recall + (1.0 - false_accept)) / 2.0,
    }


def _candidate_floors(outcomes: Sequence[QueryOutcome]) -> list[float]:
    return sorted({score for o in outcomes for _, score in o.scores} | {0.0})


def _candidate_margins(outcomes: Sequence[QueryOutcome]) -> list[float]:
    gaps = {0.0}
    for o in outcomes:
        if len(o.scores) >= 2:
            gaps.add(max(0.0, o.scores[0][1] - o.scores[1][1]))
    return sorted(gaps)


def _candidate_ratios(outcomes: Sequence[QueryOutcome]) -> list[float]:
    ratios = {1.0}
    for o in outcomes:
        if not o.scores:
            continue
        mean = sum(s for _, s in o.scores) / len(o.scores)
        if mean > 0:
            ratios.add(o.scores[0][1] / mean)
    return sorted(ratios)


def sweep_absolute(
    outcomes: Sequence[QueryOutcome], thresholds: Sequence[float] | None = None
) -> list[dict]:
    grid = list(thresholds) if thresholds is not None else _candidate_floors(outcomes)
    return [
        {
            "threshold": t,
            **metrics_at(outcomes, lambda s, t=t: accept_absolute(s, t), floor=t),
        }
        for t in grid
    ]


def sweep_margin(
    outcomes: Sequence[QueryOutcome],
    floors: Sequence[float] | None = None,
    margins: Sequence[float] | None = None,
) -> list[dict]:
    floor_grid = list(floors) if floors is not None else _candidate_floors(outcomes)
    margin_grid = list(margins) if margins is not None else _candidate_margins(outcomes)
    return [
        {
            "floor": f,
            "margin": m,
            **metrics_at(
                outcomes, lambda s, f=f, m=m: accept_margin(s, floor=f, margin=m), floor=f
            ),
        }
        for f in floor_grid
        for m in margin_grid
    ]


def sweep_relative(
    outcomes: Sequence[QueryOutcome],
    floors: Sequence[float] | None = None,
    ratios: Sequence[float] | None = None,
) -> list[dict]:
    floor_grid = list(floors) if floors is not None else _candidate_floors(outcomes)
    ratio_grid = list(ratios) if ratios is not None else _candidate_ratios(outcomes)
    return [
        {
            "floor": f,
            "ratio": r,
            **metrics_at(
                outcomes, lambda s, f=f, r=r: accept_relative(s, floor=f, ratio=r), floor=f
            ),
        }
        for f in floor_grid
        for r in ratio_grid
    ]


def _best(points: Sequence[dict], *config_keys: str) -> dict:
    """Highest balanced accuracy; ties go to the strictest rule (fewest accepts)."""
    if not points:
        return {}
    return max(
        points,
        key=lambda p: (p["balanced_accuracy"], *[p[k] for k in config_keys], -p["unanswerable_false_accept"]),
    )


def summarize(outcomes: Sequence[QueryOutcome]) -> dict:
    """The headline numbers: where the two distributions actually sit."""
    answerable_top1 = [o.scores[0][1] for o in outcomes if o.should_hit and o.scores]
    irrelevant_top1 = [o.scores[0][1] for o in outcomes if not o.should_hit and o.scores]
    lowest_answerable = min(answerable_top1) if answerable_top1 else None
    top_irrelevant = max(irrelevant_top1) if irrelevant_top1 else None
    return {
        "answerable_count": len(answerable_top1),
        "unanswerable_count": len(irrelevant_top1),
        "lowest_answerable_top1": lowest_answerable,
        "top_irrelevant_score": top_irrelevant,
        "separation_margin": (
            None
            if lowest_answerable is None or top_irrelevant is None
            else lowest_answerable - top_irrelevant
        ),
        "answerable_top1": sorted(answerable_top1, reverse=True),
        "irrelevant_top1": sorted(irrelevant_top1, reverse=True),
        "best_absolute": _best(sweep_absolute(outcomes), "threshold"),
    }


def compare_rules(outcomes: Sequence[QueryOutcome]) -> dict:
    """Each rule shape at its own best configuration, on identical outcomes."""
    return {
        "absolute": _best(sweep_absolute(outcomes), "threshold"),
        "margin": _best(sweep_margin(outcomes), "floor", "margin"),
        "relative": _best(sweep_relative(outcomes), "floor", "ratio"),
    }


def _ensure_environment() -> None:
    """Load placeholders and refuse to touch anything but the isolated test DB.

    This harness creates and deletes `kb_documents` rows, so pointing it at a dev
    or production database is a data-loss hazard, not a mistake to tolerate.
    `TEST_ADMIN_DB_URL` is exported only by `infra/test-db.sh env`, so requiring
    it pins the run to the documented test-database path.
    """
    for key, value in PLACEHOLDER_SETTINGS.items():
        os.environ.setdefault(key, value)

    if not os.environ.get("TEST_ADMIN_DB_URL"):
        raise SystemExit(
            "refusing to run: TEST_ADMIN_DB_URL is not set.\n"
            "This harness writes and deletes KB documents, so it only runs against "
            "the isolated test database.\n"
            'Run: eval "$(bash infra/test-db.sh env)"'
        )

    database_url = os.environ.get("DATABASE_URL", "")
    database = urlparse(database_url)
    host = database.hostname or ""
    if host not in _LOCAL_HOSTS:
        raise SystemExit(
            f"refusing to run: DATABASE_URL host {host!r} is not local "
            f"(expected one of {sorted(_LOCAL_HOSTS)}).\n"
            "This harness writes and deletes KB documents, so it only runs against "
            "the isolated test database.\n"
            'Run: eval "$(bash infra/test-db.sh env)"'
        )

    admin = urlparse(os.environ["TEST_ADMIN_DB_URL"])
    identity = (database.hostname, database.port, database.path)
    admin_identity = (admin.hostname, admin.port, admin.path)
    if identity != admin_identity:
        raise SystemExit(
            "refusing to run: DATABASE_URL and TEST_ADMIN_DB_URL name different "
            "databases.\n"
            "This harness writes and deletes KB documents, so it only runs against "
            "the isolated test database.\n"
            'Run: eval "$(bash infra/test-db.sh env)"'
        )

    tests_dir = str(_REPO_ROOT / "tests")
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    from _testdb import host_port

    if database.port != host_port():
        raise SystemExit(
            f"refusing to run: DATABASE_URL port {database.port!r} is not the "
            f"isolated test database port {host_port()!r}.\n"
            "This harness writes and deletes KB documents, so it only runs against "
            "the isolated test database.\n"
            'Run: eval "$(bash infra/test-db.sh env)"'
        )


# ---------------------------------------------------------------------------
# I/O shell — real model, real database. Not suite-covered by design.
# ---------------------------------------------------------------------------


def should_hit(query: CalibrationQuery, audience: str | None) -> bool:
    """Resolve the expected outcome of one query for one audience mode."""
    if query.query_class != "answerable":
        return False
    if query.visible_to == "customer":
        return True
    # An internal-only answer is reachable only where the audience filter is off.
    return audience is None


def reset_calibration_documents(session) -> None:
    """Delete only this harness's own documents, so re-runs are idempotent."""
    from sqlalchemy import delete, select

    from app.models import KbChunk, KbDocument

    ids = session.scalars(
        select(KbDocument.id).where(KbDocument.title.like(f"{TITLE_PREFIX}%"))
    ).all()
    if not ids:
        return
    session.execute(delete(KbChunk).where(KbChunk.document_id.in_(ids)))
    session.execute(delete(KbDocument).where(KbDocument.id.in_(ids)))
    session.flush()


def ingest_corpus(session, corpus: Corpus, index_title: bool = False) -> int:
    """Ingest every corpus document through the real pipeline. Returns chunk count."""
    from sqlalchemy import func, select

    from app.models import DocumentFormat, KbChunk
    from app.services import kb

    reset_calibration_documents(session)
    for doc in corpus.docs:
        kb.ingest_document(
            session,
            title=f"{TITLE_PREFIX}{doc.id}",
            fmt=DocumentFormat.MD,
            content=index_text(doc, index_title).encode("utf-8"),
            source_meta={"corpus_id": doc.id},
            actor="kb-calibration",
            visibility=doc.visibility,
        )
    session.commit()
    return int(session.scalar(select(func.count()).select_from(KbChunk)) or 0)


def retrieve_full_ranking(session, corpus: Corpus, audience) -> dict[str, tuple[tuple[str, float], ...]]:
    """One real retrieve per query, unfiltered, keyed by corpus document id."""
    from app.services import kb

    rankings: dict[str, tuple[tuple[str, float], ...]] = {}
    for query in corpus.queries:
        rows = kb.retrieve(
            session,
            query.text,
            top_k=FULL_RANKING_TOP_K,
            min_sim=FULL_RANKING_MIN_SIM,
            audience=audience,
        )
        rankings[query.id] = tuple(
            (str((row["source_meta"] or {}).get("corpus_id")), float(row["similarity"]))
            for row in rows
        )
    return rankings


def build_outcomes(
    corpus: Corpus, rankings: dict[str, tuple[tuple[str, float], ...]], audience: str | None
) -> list[QueryOutcome]:
    return [
        QueryOutcome(
            query_id=query.id,
            query_class=query.query_class,
            should_hit=should_hit(query, audience),
            relevant_doc_ids=frozenset(query.relevant_doc_ids),
            scores=tuple((d, s) for d, s in rankings.get(query.id, ()) if d is not None),
        )
        for query in corpus.queries
    ]


def rank_of_best_relevant(outcome: QueryOutcome) -> int | None:
    """1-based rank of the first relevant document, or None if it is absent.

    This is what separates "the ranking is wrong" from "the threshold is wrong":
    a relevant document ranked first at 0.45 is a calibration problem, a relevant
    document ranked twelfth is a retrieval problem, and the two need different
    fixes.
    """
    for rank, (doc_id, _) in enumerate(outcome.scores, start=1):
        if doc_id in outcome.relevant_doc_ids:
            return rank
    return None


def model_metadata(model_id: str) -> dict:
    from fastembed import TextEmbedding

    for entry in TextEmbedding.list_supported_models():
        if entry.get("model") == model_id:
            return {
                "id": model_id,
                "hf_source": (entry.get("sources") or {}).get("hf"),
                "dims": entry.get("dim"),
            }
    return {"id": model_id, "hf_source": None, "dims": None}


def run(
    json_path: Path | None,
    model: str | None,
    corpus_path: Path,
    modes: list[str | None],
    index_title: bool = False,
) -> dict:
    _ensure_environment()

    from app.db import SessionLocal
    from app.services import kb

    corpus = load_corpus(corpus_path)

    if model and model != kb.EMBED_MODEL:
        from fastembed import TextEmbedding

        kb.EMBED_MODEL = model
        kb._embedder = TextEmbedding(model_name=model)

    with SessionLocal() as session:
        chunks = ingest_corpus(session, corpus, index_title=index_title)

        runs: dict[str, dict] = {}
        for audience in modes:
            label = "unscoped" if audience is None else str(audience)
            outcomes = build_outcomes(
                corpus, retrieve_full_ranking(session, corpus, audience), audience
            )
            runs[label] = {
                "audience": audience,
                "summary": summarize(outcomes),
                "rules": compare_rules(outcomes),
                "per_query": [
                    {
                        "id": o.query_id,
                        "class": o.query_class,
                        "should_hit": o.should_hit,
                        "top1": (o.scores[0][1] if o.scores else None),
                        "accepted_at_production_0_65": accept_absolute(o.scores, 0.65),
                        "best_relevant_rank": rank_of_best_relevant(o),
                        "top": [
                            {"doc": d, "score": round(s, 4)} for d, s in o.scores[:5]
                        ],
                    }
                    for o in outcomes
                ],
            }

    report = {
        "corpus": {
            "path": str(corpus_path),
            "documents": len(corpus.docs),
            "queries": len(corpus.queries),
        },
        "model": model_metadata(kb.EMBED_MODEL),
        "chunking": {"chunk_size": kb.CHUNK_SIZE, "chunk_overlap": kb.CHUNK_OVERLAP, "chunks": chunks},
        "index_title": index_title,
        "production_threshold": kb.DEFAULT_MIN_SIM,
        "runs": runs,
    }
    if json_path:
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def _print_report(report: dict) -> None:
    model = report["model"]
    print(f"model: {model['id']} -> {model['hf_source']} ({model['dims']}d)")
    print(
        f"corpus: {report['corpus']['documents']} docs / {report['corpus']['queries']} queries "
        f"-> {report['chunking']['chunks']} chunks "
        f"(chunk_size={report['chunking']['chunk_size']}, overlap={report['chunking']['chunk_overlap']})"
    )
    print(f"indexed text: {'title + content' if report['index_title'] else 'content only'}")
    print(f"production min_sim: {report['production_threshold']}")
    for label, run_data in report["runs"].items():
        s = run_data["summary"]
        print(f"\n=== audience={label} ===")
        print(
            f"  answerable top-1: min={s['lowest_answerable_top1']} "
            f"max={max(s['answerable_top1']) if s['answerable_top1'] else None} "
            f"(n={s['answerable_count']})"
        )
        print(
            f"  irrelevant top-1: max={s['top_irrelevant_score']} "
            f"(n={s['unanswerable_count']})"
        )
        print(f"  separation margin: {s['separation_margin']}")
        best = s["best_absolute"]
        print(
            f"  best absolute: threshold={best.get('threshold')} "
            f"balanced={best.get('balanced_accuracy'):.3f} "
            f"recall={best.get('answerable_recall'):.3f} "
            f"false_accept={best.get('unanswerable_false_accept_rate'):.3f}"
        )
        for name, rule in run_data["rules"].items():
            config = {k: v for k, v in rule.items() if k in ("threshold", "floor", "margin", "ratio")}
            print(
                f"  rule {name:8s} {config} -> balanced={rule.get('balanced_accuracy'):.3f} "
                f"recall={rule.get('answerable_recall'):.3f} "
                f"false_accept={rule.get('unanswerable_false_accept_rate'):.3f}"
            )
        production = sum(1 for q in run_data["per_query"] if q["accepted_at_production_0_65"])
        should = sum(1 for q in run_data["per_query"] if q["should_hit"])
        print(f"  at the shipped 0.65: {production} of {len(run_data['per_query'])} queries accepted; {should} should have been answered")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", type=Path, default=None, help="write the full report here")
    parser.add_argument("--corpus", type=Path, default=CORPUS_PATH)
    parser.add_argument("--model", default=None, help="override the embedder (re-ingests)")
    parser.add_argument(
        "--audience",
        choices=["both", "unscoped", "customer"],
        default="both",
        help="which audience mode(s) to measure (default: both)",
    )
    parser.add_argument(
        "--index-title",
        action="store_true",
        help="embed the title as its own block before the content (measurement axis; production embeds content only)",
    )
    args = parser.parse_args(argv)

    modes: list[str | None] = {
        "both": [None, "customer"],
        "unscoped": [None],
        "customer": ["customer"],
    }[args.audience]

    report = run(args.json, args.model, args.corpus, modes, index_title=args.index_title)
    _print_report(report)
    if args.json:
        print(f"\njson: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
