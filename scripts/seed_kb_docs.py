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
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db import session_scope  # noqa: E402
from app.models import DocumentFormat, KbChunk, KbDocument, KbVisibility  # noqa: E402
from app.services import kb  # noqa: E402

__all__ = [
    "LocalDocument",
    "content_digest",
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


def inspect_kb(session: Session, documents: list[LocalDocument] | None = None) -> dict:
    """Compare `docs/kb` against the customer-visible database.

    `missing`   local documents with no row whose content matches
    `drifted`   local titles that exist in the database with different content
    `consistent` every local document is present with identical content
    """
    documents = documents if documents is not None else local_documents()
    rows = customer_documents(session)
    digests = {content_digest(row.content or "") for row in rows}
    titles = {row.title: row for row in rows}

    missing = [doc for doc in documents if doc.digest not in digests]
    drifted = [doc for doc in missing if doc.title in titles]
    fingerprint = hashlib.sha256(
        "".join(sorted(f"{doc.source_id}:{doc.digest}" for doc in documents)).encode("utf-8")
    ).hexdigest()[:12]

    return {
        "documents": len(rows),
        "chunks": _chunk_count(session),
        "local": [doc.source_id for doc in documents],
        "missing": [doc.source_id for doc in missing],
        "drifted": [doc.source_id for doc in drifted],
        "consistent": not missing,
        "fingerprint": fingerprint,
    }


def seed(session: Session, documents: list[LocalDocument], force: bool = False) -> dict:
    """Create missing documents and, with `force`, re-version drifted ones."""
    created: list[str] = []
    updated: list[str] = []
    skipped: list[str] = []

    rows = customer_documents(session)
    by_title = {row.title: row for row in rows}
    digests = {content_digest(row.content or "") for row in rows}

    for doc in documents:
        if doc.digest in digests:
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
            )
            updated.append(doc.source_id)
            continue
        kb.ingest_document(
            session,
            title=doc.title,
            fmt=DocumentFormat.MD,
            content=doc.content.encode("utf-8"),
            source_meta={"source": "docs/kb", "source_id": doc.source_id},
            actor="conv-eval",
            visibility=KbVisibility.CUSTOMER,
        )
        created.append(doc.source_id)

    session.commit()
    return {"created": created, "updated": updated, "skipped": skipped}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed the customer-visible KB from docs/kb (idempotent)."
    )
    parser.add_argument("--apply", action="store_true", help="write the missing documents")
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-version a document whose content drifted (creates a new version)",
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
        if before["consistent"]:
            print("kb · consistente con docs/kb: nada que hacer")
            return 0

        print(f"kb · faltantes: {', '.join(before['missing'])}")
        if before["drifted"]:
            print(f"kb · con contenido distinto al archivo: {', '.join(before['drifted'])}")
        if not args.apply:
            print("kb · sin cambios (pasá --apply para cargar)")
            return 1

        result = seed(session, documents, force=args.force)
        after = inspect_kb(session, documents)

    print(
        f"kb · creados {len(result['created'])} · actualizados {len(result['updated'])} "
        f"· sin cambios {len(result['skipped'])}"
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
