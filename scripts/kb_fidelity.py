"""Answer-fidelity harness for the KB RAG — Layer 2 of the KB measurement work.

Why this exists
---------------
`scripts/kb_calibration.py` measures what retrieval **returns**. It stops there: it
never calls the model. So the failure that costs the client money — the bot stating
a price, a plazo or a guarantee the retrieved chunk does not contain — has never
been observed, and no test in the suite can observe it, because every integration
and functional test intercepts the provider with `respx`
(`tests/integration/conftest.py:144-195`).

This harness drives the **real** conversation graph (`app.chat.graph.run_conversation`)
against the **real** provider and the **real** retrieval, once per labeled query, and
records what came back. It reuses the corpus, the ingest pipeline, the environment
guard and the conversation helpers that already exist rather than reimplementing any
of them.

What it measures
----------------
Per query: the outcome (`answered` / `declined` / `handed_off` / `clarified` /
`other`), the reply, the chunk set the model was given, and the numbers in the reply
that appear in no chunk. The last one is the deterministic triage core: it shrinks a
human's reading to a shortlist. It is a **flag, never a verdict** — a faithful reply
can introduce a number the chunk does not contain (a count, a date, a phone).

With `--judge`, an LLM also scores groundedness. That verdict is reported in its own
section and never merged into the deterministic counts.

What it deliberately does NOT do
--------------------------------
It adds **no production seam**. `run_conversation` returns only `list[str]`
(`app/chat/graph.py:254-267`) and the `escalate` flags live in graph state that is
discarded, so the outcome is classified from the reply text plus the persisted
state — the same discipline `scripts/chat_harness.py:118-127` follows.

The chunk set is **re-derived**, not captured: retrieval is deterministic for a
fixed database state and query, so re-running `kb.retrieve` with the arguments the
production path uses yields the same chunks. When a turn was handed off before
`respond` was reached, **no chunk reached the model at all**, and the report says so
instead of inventing one.

Usage
-----
    eval "$(bash infra/test-db.sh env)"           # required, see the ODD record
    uv run python scripts/kb_fidelity.py --limit 6        # cheap smoke run
    uv run python scripts/kb_fidelity.py --json /tmp/kb-fidelity.json
    uv run python scripts/kb_fidelity.py --judge --json /tmp/kb-fidelity-judged.json

The test-database eval is required: it is what pins the run to the isolated
database, and the harness refuses any other host. The provider key and model are
read from `infra/.env` for the provider keys only, so no sourcing is needed.

See `odd/tasks/kb-answer-fidelity.md` for the decisions and the honest limits.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Sequence
from uuid import uuid4

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (str(_REPO_ROOT), str(Path(__file__).resolve().parent)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import kb_calibration as cal  # noqa: E402

# `app.config.Settings` requires the channel secrets even for a read-only KB run.
# The same placeholders the retrieval harness uses, applied here so this module
# stays importable by the model-free unit tests.
#
# `DEEPSEEK_API_KEY` is deliberately NOT among them. This harness is the first one
# in the repo that calls the real provider, and `os.environ` is the ONLY settings
# source (`app/config.py:31`, `env_file=None`). `setdefault`ing a fake key here
# would shadow a real one and turn every paid call into a 401 — a silent,
# expensive failure.
for _key, _value in cal.PLACEHOLDER_SETTINGS.items():
    if _key != "DEEPSEEK_API_KEY":
        os.environ.setdefault(_key, _value)

# The provider keys cannot come from the process environment alone: `infra/.env` is
# read by docker-compose for the containers, not by a bare `uv run`. Sourcing that
# file wholesale is not an option either — it also carries `DATABASE_URL` pointing
# at the compose `db` service, which poisons the isolated test URL that
# `infra/test-db.sh env` derives (`infra/test-db.sh:25-27`). So only the provider
# keys are read, and only when the shell has not already set them.
#
# `CHAT_MODEL` matters as much as the key: production runs `deepseek-flash`
# (`infra/.env`), while `app/config.py:49` defaults to `deepseek-chat`. Measuring
# with the default would measure a model the product does not use.
PROVIDER_ENV_KEYS = (
    "DEEPSEEK_API_KEY",
    "OPENROUTER_API_KEY",
    "CHAT_PROVIDER",
    "CHAT_MODEL",
)
_ENV_FILES = (_REPO_ROOT / "infra" / ".env", _REPO_ROOT / ".env")


def _env_file_value(key: str) -> str | None:
    """Last `KEY=value` for `key` across the app's env files, or None."""
    for path in _ENV_FILES:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            entry = line.strip()
            if entry.startswith(f"{key}="):
                return entry.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def _load_provider_environment() -> None:
    for key in PROVIDER_ENV_KEYS:
        if key in os.environ:
            continue
        value = _env_file_value(key)
        if value:
            os.environ[key] = value


_load_provider_environment()

from app.chat.nodes.capture import CAPTURE_FIELDS, COMPLETION_REPLY  # noqa: E402
from app.chat.nodes.handoff import HANDOFF_REPLY  # noqa: E402
from app.chat.nodes.respond import CANNOT_ANSWER_REPLY, CLARIFICATION_REPLY  # noqa: E402
from app.chat.state import greeting_with_menu  # noqa: E402

OUTCOMES = (
    "answered",
    "declined",
    "handed_off",
    "emergency_protocol",
    "clarified",
    "capture_started",
    "greeted_only",
    "other",
)

# The CM-2 capture questions. A turn that asks for a field is not an answer to the
# question that was asked, and scoring it as one would invent false answers: four
# `near_miss` queries in the first full run came back as "¿Cuál es tu nombre?".
CAPTURE_PROMPTS = frozenset([question for _, question in CAPTURE_FIELDS] + [COMPLETION_REPLY])

# A number is a digit run optionally continued by `.`/`,` groups. Chilean Spanish
# uses `.` for thousands (`45.000`) and `,` for decimals (`1,5`), so the grouping is
# what disambiguates them, not the character.
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")
# Every separator group is exactly three digits -> they are thousands separators.
_GROUPED_RE = re.compile(r"^\d{1,3}(?:[.,]\d{3})+$")


# ---------------------------------------------------------------------------
# Pure core — the scoring instrument. Suite-covered and model-free.
# ---------------------------------------------------------------------------


def normalize_number(token: str) -> str:
    """Canonicalize a numeric token to a plain digit string.

    `45.000` and `45000` must compare equal, and so must `1.234.567` and
    `1234567`. A separator whose groups are not all three digits is a decimal mark:
    the fraction is dropped (`1,5` -> `1`). That is lossy on purpose — the check
    compares magnitudes, and keeping the fraction would make `1,5` and `15`
    indistinguishable from `1.5` and `1,5`.
    """
    if _GROUPED_RE.match(token):
        digits = re.sub(r"[.,]", "", token)
    else:
        digits = re.split(r"[.,]", token, maxsplit=1)[0]
    return str(int(digits))


def extract_numbers(text: str) -> set[str]:
    """Every normalized numeric token in `text`."""
    return {normalize_number(match.group(0)) for match in _NUMBER_RE.finditer(text)}


def ungrounded_numbers(reply: str, chunk_texts: Sequence[str]) -> list[str]:
    """Numbers stated in the reply that appear in none of the chunks.

    Grounding is against the whole retrieved set, not one chunk. With no chunks at
    all every number in the reply is ungrounded, which is the truthful answer: the
    reply had nothing behind it.

    The result is a **candidate list for a human**, never an automatic verdict.
    """
    grounded: set[str] = set()
    for chunk in chunk_texts:
        grounded |= extract_numbers(chunk)
    return sorted(extract_numbers(reply) - grounded)


def terminal_reply(replies: Sequence[str]) -> str | None:
    """The reply produced by the terminal node, with the CM-1 greeting removed.

    `replies` is an accumulator (`app/chat/state.py:175`), so a first-contact turn
    yields `[greeting, <terminal reply>]` and the greeting must not be read as the
    answer.
    """
    greeting = greeting_with_menu()
    terminal = [reply for reply in replies if reply != greeting]
    return terminal[-1] if terminal else None


def greeting_emitted(replies: Sequence[str]) -> bool:
    """Whether the CM-1 first-contact greeting was part of this turn's replies."""
    greeting = greeting_with_menu()
    return any(reply == greeting for reply in replies)


def classify_outcome(replies: Sequence[str], events: Sequence[dict] = ()) -> str:
    """Map one turn's replies (and the events it recorded) to its outcome.

    The emergency check comes first and reads the recorded event, not the reply
    text. The EM-3 protocol replies are ordinary free text built from
    panel-editable settings, so a reply-shape test would score a gas-leak safety
    protocol as a grounded answer — and those two queries were exactly the only
    `answered` rows in the first full run, which would have reported two KB
    answers where there were none.

    `greeted_only` is likewise a distinct outcome on purpose. On first contact the
    CM-1 menu is the reply, and `respond` deliberately stays silent when the
    classifier could not place the message (`app/chat/nodes/respond.py:121-127`).
    That is the correct behaviour for a question the bot cannot serve, and folding
    it into `other` would report a safety property as a failure.
    """
    if any(entry.get("event") == "emergency" for entry in events):
        return "emergency_protocol"
    last = terminal_reply(replies)
    if last is None:
        return "greeted_only" if greeting_emitted(replies) else "other"
    if last == CANNOT_ANSWER_REPLY:
        return "declined"
    if last == HANDOFF_REPLY:
        return "handed_off"
    if last == CLARIFICATION_REPLY:
        return "clarified"
    if last in CAPTURE_PROMPTS:
        return "capture_started"
    return "answered"


def summarize(rows: Sequence[dict]) -> dict:
    """Per-class rates. The three label classes are always present, even at n=0.

    For `answerable`, the numbers that matter are `answered_rate` (did it answer)
    and `ungrounded_flag_rate` (did it stay faithful). For the other two classes the
    correct behaviour is **not** answering, so the number that matters is
    `non_answer_rate`.
    """
    by_class: dict[str, dict] = {}
    for query_class in sorted(cal.QUERY_CLASSES):
        subset = [row for row in rows if row["class"] == query_class]
        total = len(subset)
        counts = Counter(row["outcome"] for row in subset)
        flagged = sum(1 for row in subset if row.get("ungrounded"))
        entry: dict = {"n": total, "ungrounded_flag_count": flagged}
        for kind in OUTCOMES:
            entry[kind] = counts.get(kind, 0)
        entry["answered_rate"] = entry["answered"] / total if total else 0.0
        # Everything that is not a free-text answer is a non-answer, including the
        # menu-only and capture outcomes. Computing it as a complement rather than
        # as `declined + handed_off` means a new non-answer outcome cannot silently
        # inflate the false-answer rate.
        entry["non_answer_rate"] = (total - entry["answered"]) / total if total else 0.0
        entry["ungrounded_flag_rate"] = flagged / total if total else 0.0
        by_class[query_class] = entry
    reasons = Counter(
        row["escalate_reason"] for row in rows if row.get("escalate_reason")
    )
    return {
        "total": len(rows),
        "by_class": by_class,
        # Which layer produced each handoff. A `kb_miss` is a retrieval verdict;
        # `emergency_weak_hit` and the `cost_*` labels never reached retrieval, so
        # counting them as KB failures would misreport the KB entirely.
        "handoff_reasons": dict(reasons),
    }


# ---------------------------------------------------------------------------
# I/O shell — real graph, real provider, real database. Not suite-covered.
# ---------------------------------------------------------------------------


def _retrieved_chunks(session, text: str) -> list[dict]:
    """Re-derive the chunk set `respond` fed to the model.

    The arguments are copied from `app/chat/nodes/respond.py:131-138` verbatim, so
    this reproduces the production call rather than approximating it.
    """
    from app.models import KbVisibility
    from app.services import kb

    return kb.retrieve(
        session,
        text,
        top_k=kb.DEFAULT_TOP_K,
        min_sim=kb.DEFAULT_MIN_SIM,
        audience=KbVisibility.CUSTOMER,
    )


def _conversation_events(session, conversation_id: int) -> list[dict]:
    """The events the brain recorded, each with its cause.

    The cause is what separates a KB-layer handoff (`handoff:kb_miss`) from a
    safety-layer one (`handoff:emergency_weak_hit`) or a budget one
    (`handoff:cost_daily_limit`). Without it the report would blame the KB for
    every escalation, including the ones retrieval never got to see.
    """
    from sqlalchemy import select

    from app.models import ConversationEvent

    rows = session.scalars(
        select(ConversationEvent)
        .where(ConversationEvent.conversation_id == conversation_id)
        .order_by(ConversationEvent.created_at, ConversationEvent.id)
    ).all()
    return [{"event": row.event, "cause": row.cause} for row in rows]


def _escalate_reason(events: Sequence[dict]) -> str | None:
    """The `handoff:<reason>` label the brain recorded, or None."""
    for entry in events:
        cause = entry.get("cause") or ""
        if entry.get("event") == "escalation" and cause.startswith("handoff:"):
            return cause.split(":", 1)[1]
    return None


def _intent(events: Sequence[dict]) -> str | None:
    """The classified intent, which is what chose the routing path."""
    for entry in events:
        cause = entry.get("cause") or ""
        if entry.get("event") == "classified" and cause.startswith("intent:"):
            return cause.split(":", 1)[1]
    return None


def run_query(session, query, phone: str) -> dict:
    """Drive one labeled query through the real path and score the turn."""
    import chat_harness as ch

    conversation_id = ch.ensure_conversation(session, phone)
    replies = ch.run_turn(session, conversation_id, query.text)
    chunks = _retrieved_chunks(session, query.text)

    events = _conversation_events(session, conversation_id)
    outcome = classify_outcome(replies, events)
    answer = terminal_reply(replies) or ""
    chunk_texts = [chunk["content"] for chunk in chunks]
    # Only an answer can be ungrounded. Every other outcome is a deterministic
    # constant, a capture prompt, a safety protocol or the CM-1 menu — none of
    # which makes a factual claim about the KB.
    ungrounded = ungrounded_numbers(answer, chunk_texts) if outcome == "answered" else []

    return {
        "query_id": query.id,
        "text": query.text,
        "class": query.query_class,
        "visible_to": query.visible_to,
        "conversation_id": conversation_id,
        "greeting_emitted": greeting_emitted(replies),
        "outcome": outcome,
        "intent": _intent(events),
        "escalate_reason": _escalate_reason(events),
        "reply": answer,
        "replies": list(replies),
        "events": events,
        "chunks": [
            {
                "document_id": chunk["document_id"],
                "similarity": chunk["similarity"],
                "content": chunk["content"],
            }
            for chunk in chunks
        ],
        "ungrounded": ungrounded,
    }


def _judge_row(row: dict) -> dict:
    """Ask the provider whether the reply is supported by its chunks (D7).

    Reported separately and never merged into the deterministic counts: it is a
    model's opinion, not a measurement.
    """
    from app.services.llm import CHAT_MODEL, openai_client

    chunks = "\n".join(
        f"{index + 1}. {chunk['content']}" for index, chunk in enumerate(row["chunks"])
    )
    prompt = (
        "You are auditing a customer-support answer against the only source it was "
        "given. Decide whether every factual claim in the ANSWER is supported by the "
        "SOURCES. Ignore style, tone and length. Reply with one JSON object only: "
        '{"grounded": true|false, "unsupported_claims": ["..."]}.\n\n'
        f"<sources>\n{chunks}\n</sources>\n\n"
        f"<question>{row['text']}</question>\n\n"
        f"<answer>{row['reply']}</answer>"
    )
    response = openai_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"
    try:
        verdict = json.loads(raw)
    except json.JSONDecodeError:
        return {"grounded": None, "unsupported_claims": [], "raw": raw}
    return {
        "grounded": verdict.get("grounded"),
        "unsupported_claims": verdict.get("unsupported_claims") or [],
    }


def run(limit: int = 0, query_class: str | None = None, judge: bool = False) -> dict:
    """Measure every selected query. Returns the report dict."""
    from app.config import get_settings
    from app.db import session_scope
    from app.services import kb

    settings = get_settings()
    corpus = cal.load_corpus()
    queries = [
        query
        for query in corpus.queries
        if query_class is None or query.query_class == query_class
    ]
    if limit:
        queries = queries[:limit]

    print(f"forecast: {len(queries)} queries x 1 chat completion"
          f"{' + 1 judge completion each' if judge else ''} = "
          f"{len(queries) * (2 if judge else 1)} provider calls")

    # A fresh customer per query is a correctness requirement (D3): a handoff sets
    # the conversation to `human`, and a later query in the same conversation would
    # be answered under different gates. The nonce keeps re-runs isolated too —
    # deterministic phones would make `ensure_conversation` reuse the previous
    # run's conversation, which silently suppresses the CM-1 greeting and shifts
    # `state.turn` for every query.
    run_nonce = int(uuid4().int % 100000)

    rows: list[dict] = []
    with session_scope() as session:
        chunks_ingested = cal.ingest_corpus(session, corpus)
        print(f"ingested {len(corpus.docs)} documents -> {chunks_ingested} chunks")

    for index, query in enumerate(queries, start=1):
        phone = f"+569{run_nonce:05d}{index:03d}"
        with session_scope() as session:
            row = run_query(session, query, phone)
        if judge and row["outcome"] == "answered":
            row["judge"] = _judge_row(row)
        rows.append(row)
        flag = f" ungrounded={row['ungrounded']}" if row["ungrounded"] else ""
        print(f"[{index}/{len(queries)}] {query.query_class:<13} {row['outcome']:<10}{flag}")

    report = {
        "corpus": {"documents": len(corpus.docs), "queries": len(queries)},
        # Provenance: an answer-fidelity number is only meaningful for the model and
        # the threshold it was measured on.
        "provider": settings.chat_provider,
        "model": settings.chat_model,
        "production_threshold": kb.DEFAULT_MIN_SIM,
        "judge_enabled": judge,
        "summary": summarize(rows),
        "rows": rows,
    }
    return report


def _print_report(report: dict) -> None:
    summary = report["summary"]
    print(
        f"\n=== answer fidelity — {summary['total']} queries · "
        f"{report['provider']}/{report['model']} · min_sim={report['production_threshold']} ==="
    )
    for query_class, row in summary["by_class"].items():
        print(
            f"{query_class:<14} n={row['n']:<3} answered={row['answered']:<3} "
            f"declined={row['declined']:<3} handed_off={row['handed_off']:<3} "
            f"answered_rate={row['answered_rate']:.3f} "
            f"non_answer_rate={row['non_answer_rate']:.3f} "
            f"ungrounded={row['ungrounded_flag_count']} "
            f"({row['ungrounded_flag_rate']:.3f})"
        )
    if report["summary"]["handoff_reasons"]:
        print("\nhandoffs by layer:")
        for reason, count in sorted(report["summary"]["handoff_reasons"].items()):
            layer = "KB" if reason == "kb_miss" else "not the KB"
            print(f"  {reason:<26} {count:>3}  ({layer})")
    flagged = [row for row in report["rows"] if row["ungrounded"]]
    if flagged:
        print("\nungrounded-number candidates (a flag, not a verdict):")
        for row in flagged:
            print(f"  {row['query_id']}: {row['ungrounded']} -> {row['reply'][:90]}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", dest="json_path", help="write the report here")
    parser.add_argument("--limit", type=int, default=0, help="only the first N queries")
    parser.add_argument(
        "--query-class", choices=sorted(cal.QUERY_CLASSES), help="only this class"
    )
    parser.add_argument("--judge", action="store_true", help="add an LLM groundedness verdict")
    args = parser.parse_args(argv)

    cal._ensure_environment()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit(
            "refusing to run: no DEEPSEEK_API_KEY in the environment or in "
            "infra/.env.\nThis measures the real model's answers, so it needs a real "
            "key before it\nspends provider calls. Put it in infra/.env as "
            "`DEEPSEEK_API_KEY=...` and re-run."
        )

    report = run(limit=args.limit, query_class=args.query_class, judge=args.judge)
    _print_report(report)
    if args.json_path:
        Path(args.json_path).write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\nwrote {args.json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
