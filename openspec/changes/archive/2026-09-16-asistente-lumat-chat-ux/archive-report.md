# Archive Report: Asistente Lumat Chat UX

## Final state

The change is delivered to `main` through PRs #202–#209. The final merged head is
`bb22e97a`. Eleven tracked work units are settled; one work unit required a
maintainer reset after exceeding its changed-line budget, and that accepted churn
is retained in the ledger history.

Verification took three passes. Pass 1 failed at 8/10 requirements and 17/22
scenarios. Pass 2 failed at 11/11 and 20/22 after resolving the first behavioral
findings. Pass 3 remained formally `fail` at 11/11 requirements and 21/22
scenarios: the producing-message anchoring coverage, retry resubmission, and
title fallback gaps were resolved, while the contrast scenario remained open.
The backend suite finished at 850 passed with 2 warnings; the frontend suite at
548 passed across 76 files; the focused AgentChat suite at 28 passed; TypeScript,
production build, and the eight-test browser suite passed on authoritative reruns.

After verification, the maintainer rescoped `DS-CC-5` in commit `bb22e97a`.
The requirement now applies only to contrast pairs introduced or modified by the
assistant surface and explicitly requires inherited debt to be recorded with its
ratio and attributed to a future design-system change. This archive records that
rescoping rather than the pre-amendment requirement text.

## Inherited contrast debt (opened by this change, since resolved)

`contrast-verification.md` is a first-class artifact. It records a computed
token-pair verification, not a rendered-pixel audit; no accessibility tooling was
added because that was out of scope. At archive time the following unchanged inherited
pairs remained below their applicable thresholds and required a future approved
design-system change:

- `--warning #A16207` on `--warning-bg #FEF3C7`: **4.42:1**, below 4.5:1.
- `--border #D8DDE3` on `--surface #FFFFFF`: **1.37:1**, below 3:1.
- `--border #D8DDE3` on `--bg #F1F1E8`: **1.20:1**, below 3:1.
- `--border-strong #C3CBD4` on effective `--brand-bg-elevated #EBEEE7`: **1.40:1**, below 3:1.

No token value was changed by this change. The debt was left intentionally open and is
attributed to a future design-system change, not treated as an unqualified success.

**Resolved after archiving, in commit `63c4acd1`.** The remediation turned out to be
narrower than this list implied, and one entry above was misclassified:

- **`--border` was not changed.** All sixteen of its usages are decorative separators
  (`.ai-agent-grammar__header`, `__bubble`, `__inspector section`, page cards), which
  WCAG 1.4.11 exempts because no control is identified by them. Darkening it would have
  hardened every divider in the panel for no accessibility gain.
- `--border-strong` `#C3CBD4` → `#7E858F`: **3.18:1** on the elevated background and
  **3.72:1** on white.
- `--warning` `#A16207` → `#A05E07`: **4.60:1** on the warning background. This also
  repaired a pairing the original audit did not catch — `--warning` on `--bg` was
  **4.33:1** and is now **4.51:1**.
- The assistant composer and attachment chip relied on `--corp-border`, the alias
  pointing at the decorative `--border`, for a boundary that is in fact load-bearing:
  **1.17:1**, worse than the 1.37:1 recorded above because the composer sits on
  `--brand-bg-elevated` rather than white. They now use `--border-strong`.

`tokens.test.ts` guards every remediated pair by resolving the token values, computing
the ratios, and failing below threshold, so the debt cannot return silently.

## Specs synchronized

- `internal-agent-chat`: modified `IAC-4`; added `IAC-10`–`IAC-13`.
- `ui-command-center`: modified `CC-1` and `CC-3`; added `CC-5`.
- `panel-design-system`: modified `DS-CC-1` and `DS-CC-3`; added rescoped `DS-CC-5`.

All target requirement IDs were verified in the source specs before applying the
merge. Requirements outside those IDs were preserved. The intended narrowing in
`CC-1` and the rewrite of `IAC-4` were reviewed and are recorded as intentional;
no other destructive delta was found.

## Artifact traceability

Filesystem artifacts read: `proposal.md`, all three delta specs, `design.md`,
`tasks.md`, `verify-report.md`, and `contrast-verification.md`.

Engram observations read: proposal `#3347`, consolidated delta specs `#3359`,
design `#3368`, tasks `#3375`, and verify report `#3408`. The contrast
verification had no separate Engram observation; its filesystem artifact is
preserved in the archive. No native review receipt was supplied or discovered in
the structured handoff, so no review topics are claimed here.

## Archive disposition

Intentional-with-warnings at the time of archiving: implementation was delivered and
all tasks were complete, but the inherited contrast debt was explicitly open.

That warning is now discharged. The debt was resolved in commit `63c4acd1` — see
"Inherited contrast debt" above, which records both the original finding and its
resolution. The rescoped `DS-CC-5` requirement stands unchanged as a general contract:
inherited contrast debt must be recorded with its ratio and attributed, rather than
silently tolerated or silently dropped.
