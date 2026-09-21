"""Emergency detection service (EM-1..EM-5, SS-2; design: app/services/emergency.py).

Deterministic, no-LLM keyword detection that runs BEFORE any LLM call
(design: "gates before LLM", D4 — no LLM validation on the safety path). Pure
functions only — no session/DB here; the chat gate node reads the SS-2
keyword list from settings and passes it in.

Classification semantics (deterministic; EM-5 conservative default):

- STRONG hit — a direct emergency expression. The accent-folded text matches
  a configured keyword:
  * phrase keywords ("olor a gas", "fuga de gas", "riesgo eléctrico", ...)
    match literally (word-bounded), and
  * bare-word keywords (fuga, humo, incendio, chispa, explosión, ...) match
    as whole words, EXCEPT when immediately followed by a benign qualifier
    ("de agua", "de aceite", "de refrigerante") — water/oil leaks are Lumat's
    normal service work (gasfitería), not a gas emergency, so "fuga de agua"
    is deliberately NOT a hit.
  A strong hit runs the full emergency protocol (EM-3): safety instructions +
  contacts + technician-notified, capture abandoned, case flagged, state ->
  human.
- WEAK hit — possible-risk language that is not an exact keyword: anomalous
  smells such as "huele raro"/"olor a quemado". EM-5: ambiguous -> escalate to a
  human, NEVER silently ignore.
  Bare "gas" is deliberately NOT a weak marker. Every marker here describes a
  PERCEPTION; "gas" describes a SUBJECT, so for a gasfitería it fired on the
  business's own vocabulary and escalated routine commercial questions before
  classification and retrieval. The phrasings that actually signal a leak
  ("olor a gas", "huele a gas", "fuga", "fuga de gas") are strong keywords.
  See odd/tasks/emergency-gas-weak-marker.md.
- None — no match; the normal commercial flow continues.

Accents are folded (NFD decompose + strip combining marks, then lowercase) so
accented keywords match unaccented customer text and vice versa: "explosión"
== "explosion", "monóxido" == "monoxido" (T4.1.2 gotcha).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

# EM-5: risk-adjacent language that is not an exact keyword. Deliberately
# small and conservative: anything matching escalates to a human instead of
# being ignored. The panel can promote any of these into the SS-2 keyword
# list (then they become strong hits).
#
# Every entry describes a PERCEPTION (a smell). Bare "gas" was removed: it
# describes a subject, not a risk, so it escalated every commercial question
# naming the business's own trade. The realistic leak phrasings are strong
# keywords already; what the removal leaves uncovered is pinned by
# `test_leak_phrasings_without_a_strong_keyword_are_not_detected`.
WEAK_MARKERS: tuple[str, ...] = (
    r"huele raro",  # design example
    r"huele feo",
    r"olor raro",
    r"olor extraño",
    r"olor a quemado",
    r"a quemado",
    r"olorcito",
)

# Benign qualifiers: a bare keyword (e.g. "fuga") followed by one of these is
# normal plumbing service work, not a gas emergency.
_BENIGN_QUALIFIERS = ("agua", "aceite", "refrigerante")


def fold_accents(text: str) -> str:
    """Lowercase + fold accents to ASCII base letters ("Explosión" -> "explosion")."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn").lower()


# Weak markers are folded like keywords so the compiled pattern runs against
# the same accent-folded text as the strong pattern.
_WEAK_PATTERN = re.compile(
    "|".join(fold_accents(m) for m in WEAK_MARKERS), re.IGNORECASE
)


def _keyword_fragment(keyword: str) -> str:
    """One keyword -> regex fragment (accent-folded, whole-word bounded).

    A bare-word keyword additionally rejects a benign qualifier right after
    it ("fuga de agua" does not match the "fuga" keyword).
    """
    folded = fold_accents(keyword)
    if " " in folded:
        return rf"\b{re.escape(folded)}\b"
    qualifiers = "|".join(_BENIGN_QUALIFIERS)
    return rf"\b{re.escape(folded)}(?!\s+(?:de\s+)?(?:{qualifiers})\b)"


def compile_keywords(keywords: Sequence[str]) -> re.Pattern:
    """Compile the keyword list into one detection pattern.

    Longest keyword first so a phrase ("fuga de gas") wins over its bare stem
    ("fuga") at the same position. The input sequence is READ-ONLY — it is
    copied and sorted, never mutated (the SS-2 default list is a shared
    mutable object from settings).
    """
    ordered = sorted(
        (k for k in keywords if k and k.strip()), key=len, reverse=True
    )
    return re.compile(
        "|".join(_keyword_fragment(k) for k in ordered), re.IGNORECASE
    )


def classify_emergency(text: str, pattern: re.Pattern) -> str | None:
    """Classify one message: ``"strong"`` | ``"weak"`` | None (no hit).

    ``pattern`` is the compiled keyword regex (``compile_keywords``); the weak
    markers are module-level (deterministic — not settings-configurable in
    T4.2; a panel promotion to the keyword list is the SS-2 knob).
    """
    folded = fold_accents(text)
    if not folded:
        return None
    if pattern.search(folded):
        return "strong"
    if _WEAK_PATTERN.search(folded):
        return "weak"
    return None
