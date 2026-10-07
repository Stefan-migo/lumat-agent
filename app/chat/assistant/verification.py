"""Deterministic verification gate for observable assistant effects."""

from collections.abc import Iterable

EFFECT_TOOLS: frozenset[str] = frozenset(
    {
        "memory.update",
        "memory.delete",
        "automation.create_rule",
        "project.create",
        "project.rename",
        "project.archive",
        "project.merge",
    }
)


def verification_required(
    *, dispatched_tools: Iterable[str], explicit: bool = False, handoff: bool = False
) -> tuple[bool, str]:
    """Return whether verification is required and a stable reason code.

    Precedence is effect-tool, then explicit request, then handoff, then not-required.
    Only dispatched tool identifiers and trusted boolean signals are considered.
    """
    if EFFECT_TOOLS.intersection(dispatched_tools):
        return True, "effect-tool"
    if explicit:
        return True, "explicit"
    if handoff:
        return True, "handoff"
    return False, "not-required"
