"""Shared evidence budgets used by assistant nodes and tool argument contracts."""

# Bounds responder tool evidence by characters. On the measured 38-tool catalog, a capped read-only
# chain with assistant.capabilities, dashboard.summary and customers.search needed 4,675 characters;
# quoting the full capability inventory alone used 4,019 and evicted the neighboring result. Keep
# the ceiling fixed: the projection, not budget growth, is what protects the turn from catalog growth.
_TOOL_EVIDENCE_LIMIT = 5_500
# Two listings must coexist in a turn (`conversations.list` then `customers.search`), so each result
# gets a little less than half of the evidence box.
_LISTING_EVIDENCE_SHARE = 0.45
# A detail result (one transcript or fetched page) can spend more, but must still fit in one bounded
# evidence box; the share pins that relation while each tool enforces its own byte/character bound.
_DETAIL_EVIDENCE_SHARE = 0.78
# Retrieved KB text is capped independently so it cannot crowd out the rest of the responder prompt.
_KB_EVIDENCE_LIMIT = 4_000
# Reserve room beyond page text for provenance, cursor metadata and JSON escaping.
_PAGE_METADATA_RESERVE = 400
PROJECT_READ_FILE_PAGE_LIMIT = int(_DETAIL_EVIDENCE_SHARE * _TOOL_EVIDENCE_LIMIT) - _PAGE_METADATA_RESERVE
