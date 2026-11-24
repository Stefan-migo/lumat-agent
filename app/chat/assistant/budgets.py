"""Shared evidence budgets used by assistant nodes and tool argument contracts."""

# Bounds responder tool evidence by characters. The ceiling is fixed, but it must fit the one thing a
# read-only step is usually for: a document. At 5,500 the two pages of a 5,899-byte project file evicted
# each other from the evidence (page 1 alone rendered 4,063 characters; pages 1+2 rendered 2,323 with
# page 1 gone), so the planner could never see the whole file and burned the whole step chain re-reading
# halves. 12,000 holds that file in one page and still keeps the projection, not budget growth, as the
# defense against catalog growth.
_TOOL_EVIDENCE_LIMIT = 12_000
# Two listings must coexist in a turn (`conversations.list` then `customers.search`), so each result
# gets a little less than half of the evidence box.
_LISTING_EVIDENCE_SHARE = 0.45
# A detail result (one transcript or fetched page) can spend more, but must still fit in one bounded
# evidence box; the share pins that relation while each tool enforces its own byte/character bound.
_DETAIL_EVIDENCE_SHARE = 0.85
# Retrieved KB text is capped independently so it cannot crowd out the rest of the responder prompt.
_KB_EVIDENCE_LIMIT = 4_000
# Reserve room beyond page text for provenance, cursor metadata and JSON escaping.
_PAGE_METADATA_RESERVE = 400
PROJECT_READ_FILE_PAGE_LIMIT = int(_DETAIL_EVIDENCE_SHARE * _TOOL_EVIDENCE_LIMIT) - _PAGE_METADATA_RESERVE
