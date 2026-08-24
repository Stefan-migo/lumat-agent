"""ConversationState additions for the H2 orchestrator (h2-router, PR 2).

Reduced-scale coverage for the state schema changes introduced by the
orchestrator/sub-graph slice:

- ``active_sub_agent``: which sub-agent the orchestrator selected for this turn
  (None until an orchestrate dispatch runs).
- ``triage_retry``: the bounded retry counter used by the research_triage
  sub-graph (AO-8, ≤1 retry before handoff).

RED-first: the fields are added to ``ConversationState`` in task 2.2, so a
constructed instance without them raises AttributeError until they land.
"""

from __future__ import annotations

from app.chat.state import ConversationState


def _state() -> ConversationState:
    return ConversationState(customer_id=1, conversation_id=1, phone="+56900000000")


def test_orphan_state_additions_defaults():
    # Orchestrator state additions default to "no sub-agent selected" and
    # "no retry yet" — a fresh conversation starts outside any sub-graph.
    state = _state()
    assert state.active_sub_agent is None
    assert state.triage_retry == 0


def test_orphan_state_additions_settable():
    # The sub-graph writes its selected sub-agent and retry count back into
    # the dataclass (returned by the node as field updates).
    state = _state()
    state.active_sub_agent = "research_triage"
    state.triage_retry = 1
    assert state.active_sub_agent == "research_triage"
    assert state.triage_retry == 1
