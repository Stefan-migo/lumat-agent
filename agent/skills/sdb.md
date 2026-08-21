# SDB (Deterministic Behavior Database)

Reference only. The authoritative SDB is the set of deterministic gate nodes in `app/chat/nodes/` (`respond`, `classify_intent`, `emergency`, `handoff_gate`) and the injection pattern set in `classify_intent.py`. This file is NEVER loaded into any LLM prompt.