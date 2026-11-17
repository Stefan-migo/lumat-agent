# Conversations inbox redesign
Objective: Restructure the panel conversation list and thread using the existing Lumat design system.
Branch: `odd/frontend` · Delivery: single review slice, under 400 authored changed lines (forecast) · Verification: Vitest, TypeScript/Vite build, Chromium.

## Specs

- S1 — “si eso necesito vamos con conversaciones como el primero redise;o lista + hilo.” Desktop shows the queue beside the selected thread; mobile retains a compact list and a focused thread as two screens. Preserve existing conversation URLs and queue filters, and show a useful empty selection state.
- S2 — “el hilo tiene que se lo mas parecido a la experiencia whatsapp.” Prioritize identity, message bubbles, and an accessible fixed-in-layout composer with secondary tools. Preserve Lumat styling, human ownership, 24-hour reply rules, attachments, and delivery feedback. Check narrow/mobile and desktop rendering without claiming physical-device keyboard coverage.
- S3 — “la idea aqui es solo trabajr frontend de forma que cuando tengamos que mergear no se haya tocado nada extra”. No backend, API, infrastructure, unrelated pages, or PWA changes. Retain the previous mobile opening fix. Use the local fixture preview for before/after review.

## Tasks

- [x] T1 · S2–S3 · inline · conversation thread layout and message-following behavior · `c62eeda9` · RED reproduced; thread/composer checks passed.
- [x] T2 · S1–S3 · inline · compact queue and responsive split view · `60a3b1a3` · RED reproduced; split layout, route, and shell checks passed.

## Log

- L1: si eso necesito vamos con conversaciones como el primero redise;o lista + hilo. el hilo tiene que se lo mas parecido a la experiencia whatsapp.
- L2: Baseline `69d9a12b7` plus existing uncommitted mobile open-action changes in four frontend files. Graph consulted ConversationThread ↔ AppShell and ConversationsList → api.ts. Preserve the API and route seams; use the isolated fixture preview.
- L3: Chromium verified the original conversation route and a reachable composer at 320, 390, 768, 1024, and 1440px, including simulated viewport reduction at 390px. Responsive rendering exposed inherited outbound text on a light background and tablet chrome consuming composer space; both corrected and rechecked. Physical mobile keyboards remain unverified.
- L4: Final gate: `npm run build` passed; `npm test -- --maxWorkers 4` passed (1,423 tests across 121 files). Targeted check: 113 tests passed. Browser probe verified switching threads in the desktop queue, restored filter after mobile back, direct-entry back, and no clipped send control. Native review was not due for the source commits (under budget). The fixture-only preview is on localhost:5175. No delivery operation authorized.
