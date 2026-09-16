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

## Open inherited contrast debt

`contrast-verification.md` is a first-class artifact. It records a computed
token-pair verification, not a rendered-pixel audit; no accessibility tooling was
added because that was out of scope. The following unchanged inherited pairs remain
below their applicable thresholds and require a future approved design-system
change:

- `--warning #A16207` on `--warning-bg #FEF3C7`: **4.42:1**, below 4.5:1.
- `--border #D8DDE3` on `--surface #FFFFFF`: **1.37:1**, below 3:1.
- `--border #D8DDE3` on `--bg #F1F1E8`: **1.20:1**, below 3:1.
- `--border-strong #C3CBD4` on effective `--brand-bg-elevated #EBEEE7`: **1.40:1**, below 3:1.

No token value was changed by this change. The debt is intentionally open and is
attributed to a future design-system change, not treated as an unqualified success.

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

Intentional-with-warnings: implementation is delivered and all tasks are complete,
but the inherited contrast debt remains explicitly open under the rescoped
requirement.
