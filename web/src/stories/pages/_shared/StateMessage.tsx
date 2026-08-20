/** Shared state banner (design D3; DS-UI-FRAME). Promoted from the Dashboard
 *  story so every page consumes one banner language. Renders a semantic
 *  status/alert region pairing a tone accent, a tinted surface, and a visible
 *  label — color is never the only channel. Loading shows the shipped spinner
 *  indicator.
 *
 *  The component is self-styling: it injects its own base `.dashboard-state`
 *  layout styles (kept from the Dashboard proving ground class names) so any
 *  page frame consumes it identically. Dashboard additionally scopes these
 *  classes under `.dashboard-shell` with the same values, so the regression
 *  sentinel's look is unchanged. */
export type StateTone = "info" | "warning" | "danger";
export type StateRole = "status" | "alert";

const STATE_TONES: Record<StateTone, { accent: string; background: string; border: string }> = {
  info: { accent: "var(--info)", background: "var(--surface)", border: "var(--border-strong)" },
  warning: { accent: "var(--warning)", background: "var(--warning-bg)", border: "var(--warning-border)" },
  danger: { accent: "var(--danger)", background: "var(--danger-bg)", border: "var(--danger-border)" },
};

const STATE_STYLES = `
  .dashboard-state {
    display: flex;
    gap: var(--space-3);
    align-items: flex-start;
    padding: var(--space-4);
    border: 1px solid;
    border-left-width: var(--space-1);
    border-radius: var(--radius-md);
  }

  .dashboard-state__spinner {
    margin-top: var(--space-1);
    border-top-color: var(--info);
  }

  .dashboard-state__body {
    display: grid;
    gap: var(--space-1);
  }

  .dashboard-state__title {
    margin: 0;
    font-size: var(--text-lg);
    font-weight: var(--weight-bold);
    line-height: var(--leading-tight);
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
      style={{ background: tokens.background, borderColor: tokens.border, borderLeftColor: tokens.accent }}
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
