# Tasks: Panel Grammar — Global Appearance, Control-Room Physiology

Delivered inside the first Clientes slice so the delta ships with its first
consumer.

- [ ] **T1** — Apply the `DS-GRAMMAR-1` delta to
  `openspec/changes/panel-grammar-global/specs/panel-design-system/spec.md`.
- [ ] **T2** — State the two axes in `web/DESIGN_SYSTEM.md`: a row in
  "Direction at a glance" and a "Grammar scope — two axes" subsection.
- [ ] **T3** — Apply the appearance axis to the first dense surface
  (`ClientesList` + `ClientFicha`) in the pilot tasks of
  `odd/tasks/clientes-product-register.md`, proving the amended contract has a
  real consumer.
- [ ] **T4** — Verify: no bubble, composer, thread rail, or inspector is rendered
  on either Clientes surface, and the data presentation remains tabular
  (`DS-GRAMMAR-1` new scenario).
- [ ] **T5** — Archive this change after the pilot's first slice merges, syncing
  the delta into `openspec/specs/panel-design-system/spec.md`.

## Notes

- `panel-app` needs no delta: the duplicate clause lived in the former
  `PNL-APP-12`, which `panel-conversaciones-redesign` replaced with
  `PNL-APP-12 — Conversation Workspace Context` and no dense-page clause.
- `tokens.css` is not touched by this change (`DS-TKN-2`).
