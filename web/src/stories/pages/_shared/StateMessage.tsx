export { StateMessage } from "../../../components/shared/StateMessage";
export type { StateMessageProps, StateRole, StateTone } from "../../../components/shared/StateMessage";

/** Shared state banner (design D3; DS-UI-FRAME). Promoted from the Dashboard
 *  story so every page consumes one banner language. Subtle inline variant:
 *  a 4px semantic-color bar on the left over a near-white tinted surface
 *  (`--*-tint`), with the visible label rendered in the semantic tone — color
 *  is never the only channel (the visible label + `role="status"`/`"alert"`
 *  carry the message).
 *
 *  The component is self-styling: it injects its own base `.dashboard-state`
 *  layout styles (kept from the Dashboard proving ground class names) so any
 *  page frame consumes it identically. Dashboard additionally scopes these
 *  classes under `.dashboard-shell` with the same values, so the regression
 *  sentinel's look is unchanged.
 *
 *  Neutral tones (`loading`, `empty`, `stale`, `partial`, `fatal`,
 *  `permission`) are not exposed by this component yet — they belong on the
 *  Dashboard proving ground and use the same `.dashboard-state` classes with
 *  the accent + tint dropped, leaving just the muted label.
 *
 *  Alert-compat (slice-1 · D5): this component is the minimal Alert mapping —
 *  it pairs a visible Spanish label, a semantic tint/accent, and
 *  `role="status"|"alert"` (never color alone, CST-PRIM-4/5). The inline
 *  `.dashboard-state` styles are NOT refactored to BEM this slice (budget); the
 *  label + role carry the message independent of styling. */
