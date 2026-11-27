"""The two shapes a customer message can take when it names her own visit.

Measured production case (2026-11-27, conversation 50): «Tengo una visita para el
lunes, puedes confirmarme que técnico va?» and «Tengo una hora agendada para el
lunes» were asked about appointment 24 — `booked`, 30/11 14:00, technician
assigned. No code path read that appointment: the first turn was answered with
free slots by `configured_answers.availability_reply` and the second was stored as
a day preference by `capture`, whose acknowledgement says the visit is not booked
yet.

Two predicates live here, and both the router (`orchestrate`) and the answer
(`configured_answers.appointment_status_reply`) read them from this module, so the
destination and the answer cannot disagree. `asks_for_change` moved here for the
same reason: a request to move the visit names the visit too, and the status
answer must yield to `manage` on it.
"""

from __future__ import annotations

import re
import unicodedata

# Possession, not vocabulary: "mi visita", "tengo una hora", "visita agendada".
# A bare "visita" or "hora" is the free-agenda and configured-hours vocabulary and
# must keep its own answers ("¿tienen hora el lunes?", "¿hasta qué hora abren?").
_BOOKED_VISIT_PATTERNS = (
    r"\bmi(?:s)?\s+(?:visita|visitas|hora|horas|agendamiento|tecnico)\b",
    r"\btengo\s+(?:una\s+|un\s+|la\s+|mi\s+)?(?:visitas?|horas?|agendad\w+|reserv\w+|tecnico)\b",
    r"\b(?:visita|hora)\s+(?:agendada|agendadas|agendado|reservada|confirmada|pendiente)\b",
    r"\bagendad[oa]s?\s+(?:para|el|la|los|las|este|esta)\b",
    r"\bconfirmar\w*\s+(?:mi|mis|la|las|el|los)\s+(?:visita|visitas|hora|horas)\b",
    r"\b(?:que|quien|cual)\s+(?:es\s+)?(?:el|la|mi)?\s*(?:tecnico|tecnica)\b",
    r"\bquien\s+(?:va|viene|ira|iria|llega|llegara)\b",
    r"\ba\s+que\s+hora\s+(?:va|viene|llega|es|tengo|queda|pasaria)\b",
)
_BOOKED_VISIT_RE = re.compile("|".join(_BOOKED_VISIT_PATTERNS))

# An explicit request to move, cancel or void the visit (S12). Moved verbatim from
# `orchestrate` so the router and the status answer share one definition.
_CHANGE_REQUEST_RE = re.compile(
    r"\b(?:reagend\w*|cancel\w*|anul\w*"
    r"|cambiar\s+(?:la|el|mi|de)\s+(?:visita|hora|dia|fecha|mantencion|mantenimiento)"
    r"|mover\s+(?:la|el|mi|de)\s+(?:visita|hora|dia|fecha|mantencion|mantenimiento))\b"
)


def normalise(text: str) -> str:
    """Case-fold and remove accents, so the patterns match either spelling."""
    decomposed = unicodedata.normalize("NFKD", (text or "").casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def asks_for_change(text: str) -> bool:
    """True when the turn explicitly asks to move, cancel or void the visit (S12).

    S1 lets a mid-capture question reach the answering path first. This is the
    carve-out that keeps S12 intact: the customer's own words name the visit and
    the action, so the turn is a request, not a question about availability.
    """
    return _CHANGE_REQUEST_RE.search(normalise(text)) is not None


def asks_about_booked_visit(text: str) -> bool:
    """True when the turn asks about the visit the customer already holds.

    A change request is excluded on purpose: "necesito cambiar la fecha de mi
    visita" names the visit, and its destination is `manage`, not a status
    summary the customer did not ask for.
    """
    normalized = normalise(text)
    if not normalized or asks_for_change(text):
        return False
    return _BOOKED_VISIT_RE.search(normalized) is not None
