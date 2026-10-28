"""Seed the customer-visible knowledge base from `docs/kb` (ODD: chatbot-conv-eval, E0).

Why this exists
---------------
The conversation evaluation is only meaningful against a database that can
answer. Today the four customer documents live in `docs/kb/*.md`, and there is no
script that loads them into a database: they were uploaded by hand into the
developer harness. A new worktree gets a new, empty database, so every price,
coverage or schedule question would become a `kb_miss` and the evaluation would
measure an empty KB instead of the bot.

This module is the missing seam. It is idempotent, it never edits a document it
did not create unless `--force` is passed, and `conv_eval.py` refuses to run
until it reports the local files and the database agree.

Usage
-----
    eval "$(bash infra/test-db.sh env)"
    uv run python scripts/seed_kb_docs.py            # report only
    uv run python scripts/seed_kb_docs.py --apply    # create the missing ones
    uv run python scripts/seed_kb_docs.py --apply --force   # re-version drift
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# `app.config.Settings` is fail-fast: five webhook/panel values are required even
# though seeding the KB touches neither. Both repo-root scripts fill only the
# unset ones with placeholders and never invent a credential. This has to run
# BEFORE the `app.*` imports below — Settings is built at import time.
_DEV_ONLY_SETTINGS = (
    "APP_SECRET",
    "VERIFY_TOKEN",
    "META_ACCESS_TOKEN",
    "META_PHONE_NUMBER_ID",
    "PANEL_SESSION_SECRET",
)


def ensure_dev_env() -> None:
    """Fill the non-secret settings the app demands when a real env is absent."""
    for name in _DEV_ONLY_SETTINGS:
        os.environ.setdefault(name, f"conv-eval-{name.lower()}")


ensure_dev_env()

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db import session_scope  # noqa: E402
from app.models import DocumentFormat, KbChunk, KbDocument, KbVisibility  # noqa: E402
from app.services import kb  # noqa: E402

__all__ = [
    "LocalDocument",
    "content_digest",
    "ensure_dev_env",
    "inspect_kb",
    "local_documents",
    "main",
    "seed",
]

KB_DIR = _REPO_ROOT / "docs" / "kb"


def _normalise(text: str) -> str:
    """Compare content by meaning-preserving shape, not by byte identity.

    Line order matters; surrounding and repeated blank lines do not. A file that
    was re-wrapped by an editor is the same document.
    """
    return "\n".join(line.strip() for line in text.strip().splitlines() if line.strip())


def content_digest(text: str) -> str:
    return hashlib.sha256(_normalise(text).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LocalDocument:
    source_id: str
    title: str
    content: str

    @property
    def digest(self) -> str:
        return content_digest(self.content)


def _title_of(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def local_documents(kb_dir: Path = KB_DIR) -> list[LocalDocument]:
    """Read every markdown document under `docs/kb`, in stable order."""
    documents = []
    for path in sorted(kb_dir.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        documents.append(
            LocalDocument(
                source_id=path.stem,
                title=_title_of(content, path.stem),
                content=content,
            )
        )
    return documents


def customer_documents(session: Session) -> list[KbDocument]:
    return list(
        session.scalars(
            select(KbDocument)
            .where(KbDocument.visibility == KbVisibility.CUSTOMER, KbDocument.active.is_(True))
            .order_by(KbDocument.id)
        )
    )


def _chunk_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(KbChunk)) or 0


def _active_chunk_meta(session: Session, doc: KbDocument) -> dict:
    """Routing metadata of the ACTIVE version, read off its first chunk."""
    chunk = session.scalars(
        select(KbChunk)
        .where(KbChunk.document_id == doc.id, KbChunk.version == doc.active_version)
        .order_by(KbChunk.chunk_index)
        .limit(1)
    ).first()
    return dict((chunk.source_meta or {}) if chunk is not None else {})


def _has_routing(meta: dict, source_id: str) -> bool:
    return meta.get("source_id") == source_id


def inspect_kb(session: Session, documents: list[LocalDocument] | None = None) -> dict:
    """Compare `docs/kb` against the customer-visible database.

    `missing`   local documents with no row whose content matches
    `drifted`   local titles that exist in the database with different content
    `unrouted`  local documents whose active version lost its routing metadata,
                so topic routing cannot find them even though the text matches
    `consistent` every local document is present with identical content
    """
    documents = documents if documents is not None else local_documents()
    rows = customer_documents(session)
    digests = {content_digest(row.content or "") for row in rows}
    titles = {row.title: row for row in rows}

    missing = [doc for doc in documents if doc.digest not in digests]
    drifted = [doc for doc in missing if doc.title in titles]
    unrouted = [
        doc.source_id
        for doc in documents
        if doc.digest in digests
        and doc.title in titles
        and not _has_routing(_active_chunk_meta(session, titles[doc.title]), doc.source_id)
    ]
    fingerprint = hashlib.sha256(
        "".join(sorted(f"{doc.source_id}:{doc.digest}" for doc in documents)).encode("utf-8")
    ).hexdigest()[:12]

    return {
        "documents": len(rows),
        "chunks": _chunk_count(session),
        "local": [doc.source_id for doc in documents],
        "missing": [doc.source_id for doc in missing],
        "drifted": [doc.source_id for doc in drifted],
        "unrouted": unrouted,
        "consistent": not missing,
        "fingerprint": fingerprint,
    }


def seed(session: Session, documents: list[LocalDocument], force: bool = False) -> dict:
    """Create missing documents, re-version drifted ones, repair unrouted ones.

    `force` authorizes both writes that change a stored document: a new version
    for drifted content, and an in-place rewrite of routing metadata for a
    document whose text already matches. The second is a metadata repair, not a
    content change: identical text is never re-embedded.
    """
    created: list[str] = []
    updated: list[str] = []
    repaired: list[str] = []
    skipped: list[str] = []

    rows = customer_documents(session)
    by_title = {row.title: row for row in rows}
    digests = {content_digest(row.content or "") for row in rows}

    for doc in documents:
        routing_meta = {"source": "docs/kb", "source_id": doc.source_id}
        if doc.digest in digests:
            existing = by_title.get(doc.title)
            if (
                force
                and existing is not None
                and not _has_routing(_active_chunk_meta(session, existing), doc.source_id)
            ):
                kb.repair_source_meta(
                    session, existing.id, source_meta=routing_meta, actor="conv-eval"
                )
                repaired.append(doc.source_id)
                continue
            skipped.append(doc.source_id)
            continue
        existing = by_title.get(doc.title)
        if existing is not None:
            if not force:
                skipped.append(doc.source_id)
                continue
            kb.update_document(
                session,
                existing.id,
                new_content=doc.content,
                title=doc.title,
                actor="conv-eval",
                source_meta=routing_meta,
            )
            updated.append(doc.source_id)
            continue
        kb.ingest_document(
            session,
            title=doc.title,
            fmt=DocumentFormat.MD,
            content=doc.content.encode("utf-8"),
            source_meta=routing_meta,
            actor="conv-eval",
            visibility=KbVisibility.CUSTOMER,
        )
        created.append(doc.source_id)

    session.commit()
    return {
        "created": created,
        "updated": updated,
        "repaired": repaired,
        "skipped": skipped,
    }


def _print_drift_summary() -> None:
    """Print the static KB drift summary without affecting seed outcomes."""
    try:
        import kb_doc_drift

        tolerated, new = kb_doc_drift.summarize()
        keys = len({finding.key for finding in tolerated})
        print(f"kb drift · tolerados: {len(tolerated)} hallazgos ({keys} claves) · nuevos: {len(new)}")
        for finding in new:
            print(f"kb drift · nuevo: {finding.source_id}|{finding.kind}|{finding.value}")
    except Exception as exc:
        # The seed's database consistency result remains authoritative; drift is
        # an advisory report and must not alter its exit status.
        print(f"kb drift · reporte no disponible: {exc}")


def main(argv: list[str] | None = None) -> int:
    ensure_dev_env()
    parser = argparse.ArgumentParser(
        description="Seed the customer-visible KB from docs/kb (idempotent)."
    )
    parser.add_argument("--apply", action="store_true", help="write the missing documents")
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "re-version a document whose content drifted, and repair the routing "
            "metadata of a document that lost it (no re-embed)"
        ),
    )
    args = parser.parse_args(argv)

    documents = local_documents()
    if not documents:
        print(f"no documents found in {KB_DIR}", file=sys.stderr)
        return 2

    with session_scope() as session:
        before = inspect_kb(session, documents)
        print(
            f"kb · {before['documents']} documentos customer · {before['chunks']} chunks "
            f"· fingerprint {before['fingerprint']}"
        )
        _print_drift_summary()
        if before["consistent"] and not before["unrouted"]:
            print("kb · consistente con docs/kb: nada que hacer")
            return 0

        if before["missing"]:
            print(f"kb · faltantes: {', '.join(before['missing'])}")
        if before["drifted"]:
            print(f"kb · con contenido distinto al archivo: {', '.join(before['drifted'])}")
        if before["unrouted"]:
            print(
                "kb · sin ruteo por tema (source_meta.source_id perdido): "
                f"{', '.join(before['unrouted'])}"
            )
        if not args.apply:
            print("kb · sin cambios (pasá --apply para cargar)")
            return 1

        result = seed(session, documents, force=args.force)
        after = inspect_kb(session, documents)

    print(
        f"kb · creados {len(result['created'])} · actualizados {len(result['updated'])} "
        f"· reparados {len(result['repaired'])} · sin cambios {len(result['skipped'])}"
    )
    print(
        f"kb · ahora {after['documents']} documentos · {after['chunks']} chunks "
        f"· fingerprint {after['fingerprint']}"
    )
    if not after["consistent"]:
        still = ", ".join(after["missing"])
        print(
            f"kb · sigue inconsistente ({still}); si el contenido cambió, pasá --force",
            file=sys.stderr,
        )
        return 1
    if after["unrouted"]:
        still = ", ".join(after["unrouted"])
        print(
            f"kb · sigue sin ruteo ({still}); pasá --force para repararlo",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
