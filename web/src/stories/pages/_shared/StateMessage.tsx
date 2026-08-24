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
export type StateTone = "info" | "warning" | "danger" | "success";
export type StateRole = "status" | "alert";

const STATE_TONES: Record<StateTone, { accent: string; tint: string }> = {
  info: { accent: "var(--info)", tint: "var(--info-tint)" },
  warning: { accent: "var(--warning)", tint: "var(--warning-tint)" },
  danger: { accent: "var(--danger)", tint: "var(--danger-tint)" },
  // Positive/confirmed outcome (e.g. Settings saved) — DESIGN_SYSTEM state hierarchy.
  success: { accent: "var(--success)", tint: "var(--success-tint)" },
};

const STATE_STYLES = `
  .dashboard-state {
    display: flex;
    gap: var(--space-3);
    align-items: center;
    padding: var(--space-3) var(--space-4);
    border-left: 4px solid;
    border-radius: var(--radius-md);
  }

  .dashboard-state__spinner {
    border-top-color: var(--info);
  }

  .dashboard-state__body {
    display: grid;
    gap: var(--space-1);
    min-width: 0;
  }

  .dashboard-state__title {
    margin: 0;
    font-size: var(--text-md);
    font-weight: var(--weight-semibold);
    line-height: var(--leading-snug);
  }

  .dashboard-state__detail {
    margin: 0;
    color: var(--text-muted);
    font-size: var(--text-sm);
    line-height: var(--leading-normal);
  }

  @media (prefers-reduced-motion: reduce) {
    .dashboard-state__spinner {
      animation: none;
    }
  }
`;

export interface StateMessageProps {
  tone: StateTone;
  role: StateRole;
  title: string;
  detail?: string;
  /** Show the shipped spinner indicator next to the title (loading only). */
  spinner?: boolean;
}

export function StateMessage({ tone, role, title, detail, spinner = false }: StateMessageProps) {
  const tokens = STATE_TONES[tone];
  return (
    <section
      role={role}
      className="dashboard-state"
      style={{ background: tokens.tint, borderLeftColor: tokens.accent }}
    >
      <style>{STATE_STYLES}</style>
      {spinner ? <span className="spinner__indicator dashboard-state__spinner" aria-hidden="true" /> : null}
      <div className="dashboard-state__body">
        <h2 className="dashboard-state__title" style={{ color: tokens.accent }}>{title}</h2>
        {detail ? <p className="dashboard-state__detail">{detail}</p> : null}
      </div>
    </section>
  );
}
