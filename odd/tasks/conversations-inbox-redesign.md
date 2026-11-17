# Conversations inbox redesign
Objective: Restructure the panel conversation list and thread using the existing Lumat design system.
Branch: `odd/frontend` · Delivery: single review slice, under 400 authored changed lines (forecast) · Verification: Vitest, TypeScript/Vite build, Chromium.

## Specs

- S1 — “si eso necesito vamos con conversaciones como el primero redise;o lista + hilo.” Desktop shows the queue beside the selected thread; mobile retains a compact list and a focused thread as two screens. Preserve existing conversation URLs and queue filters, and show a useful empty selection state.
- S2 — “el hilo tiene que se lo mas parecido a la experiencia whatsapp.” Prioritize identity, message bubbles, and an accessible fixed-in-layout composer with secondary tools. Preserve Lumat styling, human ownership, 24-hour reply rules, attachments, and delivery feedback. Check narrow/mobile and desktop rendering without claiming physical-device keyboard coverage.
- S3 — “la idea aqui es solo trabajr frontend de forma que cuando tengamos que mergear no se haya tocado nada extra”. No backend, API, infrastructure, unrelated pages, or PWA changes. Retain the previous mobile opening fix. Use the local fixture preview for before/after review.

## Tasks

- [x] T1 · S2–S3 · inline · conversation thread layout and message-following behavior; RED reproduced, thread/composer checks passed.
- [ ] T2 · S1–S3 · inline · restructure the queue and compose the responsive split view; verify both viewport flows and existing navigation.

## Log

- L1: si eso necesito vamos con conversaciones como el primero redise;o lista + hilo. el hilo tiene que se lo mas parecido a la experiencia whatsapp.
- L2: Baseline `69d9a12b7` plus existing uncommitted mobile open-action changes in four frontend files. Graph consulted ConversationThread ↔ AppShell and ConversationsList → api.ts. Preserve the API and route seams; use the isolated fixture preview.
- L3: Chromium verified the original conversation route and a reachable composer at 320, 390, 768, 1024, and 1440px, including simulated viewport reduction at 390px. Responsive rendering exposed inherited outbound text on a light background and tablet chrome consuming composer space; both corrected and rechecked. Physical mobile keyboards remain unverified.
