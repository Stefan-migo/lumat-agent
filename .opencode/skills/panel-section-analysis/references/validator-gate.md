# Validator Gate — panel-section-analysis

**Role**: fresh-context, read-only. You did not write these findings. Your job is to **reject**,
not to fix.

**Input**: the analyst's new ledger rows for ONE section, plus the section's reference paths,
code map, and the owner's visual analysis.

**Output**: exactly one verdict.

```
verdict: PASS | REJECT
rows_checked: N
rejected:
  - id: <ID>
    reason: <schema|evidence|classification|duplicate|palette-reopen>
    detail: <one line>
```

## Checks (in order)

1. **Schema** — the row has every column; `Class`, `Severity`, and `Section` use only the
   allowed values; `ID` is `<section>-NNN` and unique in the ledger.
2. **Evidence** — all three attestations are present and specific: the reference file exists,
   the code anchor resolves to a real `<path>:<line>`, and the owner note is verbatim or the
   literal `owner did not flag`.
3. **Classification** — re-derive the class from `Fix scope`, independent of the analyst's
   label. A row whose fix scope includes `web/src/components/primitives/*`, `PanelShell.tsx`,
   `AppShell.tsx`, or `panelRoutes.ts` **must** be `shared-primitive`; one touching
   `tokens.css` **must** be `token-palette`. Misclassification is a REJECT.
4. **No silent palette reopen** — a `token-palette` row must be marked as an escalation, not a
   proposed fix.
5. **No duplicate** — the finding is not already in the ledger.

## Rules

- Read-only. Never edit the ledger, never fix a row, never propose the fix.
- Reject on any failed check; do not partially accept a row.
- If you cannot inspect something (missing file, unresolvable anchor), that is a REJECT with
  `reason: evidence`, not a PASS.
- Do not add opinions, design taste, or new findings of your own.
