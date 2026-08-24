# Delta for Agent Config

## Purpose

Declare the multi-agent registry as data with a defined schema: one top-level `orchestrator` entry plus a sub-agent roster, each with the seven declared fields. Enforcement stays at the orchestrator dispatch boundary only — backward-compatible with AC-4's data-only stance (no runtime scope enforcement outside dispatch).

## MODIFIED Requirements

### Requirement: AC-4 — Data-Only Registry

The system MUST declare agents in `registry.yaml` as data with a defined schema: the top-level `orchestrator` entry (per D-A7) plus a multi-agent sub-agent roster. The registry MUST NOT enforce tools, KB scope, or memory scope beyond the orchestrator dispatch boundary (AO-2/AO-6/AO-7).
(Previously: the registry declared exactly one agent `orchestrator`; no runtime reader or consumer existed, enforcement deferred to H2.)

#### Scenario: Declarative, one orchestrator
- GIVEN `registry.yaml` parses at boot
- THEN it resolves exactly one top-level `orchestrator` per schema
- AND the multi-agent roster is present as data
- AND no tools, KB-scope, or memory-scope rule enforces outside dispatch

#### Scenario: Reader lives outside prompts/respond
- GIVEN the startup registry reader is wired
- THEN `app/services/prompts.py` and `app/chat/nodes/respond.py` do not read `registry.yaml`

## Boundary

No DB tables or migrations for the registry (data lives in `agent/registry.yaml`); no runtime enforcement outside the orchestrator dispatch boundary (AO-2/AO-6/AO-7); `prompts.py` and `respond.py` remain non-consumers of the registry.
