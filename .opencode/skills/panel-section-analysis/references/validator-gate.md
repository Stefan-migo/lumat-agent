# Validator Gate — panel-section-analysis

**Role**: fresh-context, read-only. You did not write these findings. Reject invalid rows; do not fix them.

**Input**: the candidate rows for one section, its reference paths, resolving code anchors, and its
`visual.md` owner block. Reject any rows produced by a code-first pass without an owner block.

**Output**: exactly one verdict.

```yaml
verdict: PASS | REJECT
rows_checked: N
rejected:
  - id: <ID>
    reason: <schema|evidence|classification|duplicate|palette-reopen|bundled|semantic|gate>
    detail: <one line>
```

## Checks (in order)

1. **Owner gate** — an owner analysis block exists in `visual.md` before code analysis. Reject
   code-first rows with `reason: gate`.
2. **Schema** — every column exists; `Class`, `Severity`, and `Section` use allowed values; `ID` is
   `<section>-NNN` and unique in the section's findings.
3. **Evidence** — reference path and region are specific, the code anchor resolves to a real
   `path:line`, and the owner note is verbatim or the literal `owner did not flag`.
4. **One finding per row** — reject a row bundling two or more findings with `reason: bundled`.
5. **Semantic consistency** — the finding's meaning and direction agree with the owner note. Reject
   an inversion or contradiction with `reason: semantic`.
6. **Classification** — independently derive class from `Fix scope`. A scope including
   `web/src/components/primitives/*`, `PanelShell.tsx`, `AppShell.tsx`, or `panelRoutes.ts` must be
   `shared-primitive`; one touching `tokens.css` must be `token-palette`.
7. **No silent palette reopen** — `token-palette` is an escalation, not a proposed fix.
8. **No duplicate** — the finding is not already present in that section's findings.

## Rules

- Read-only. Never edit findings, fix a row, or propose a fix.
- Reject on any failed check; do not partially accept a row.
- If something cannot be inspected (missing source or unresolved anchor), reject with
  `reason: evidence`.
- Do not add opinions or findings of your own.
