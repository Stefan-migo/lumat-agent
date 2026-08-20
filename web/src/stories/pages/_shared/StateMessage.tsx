/** Shared state banner (design D3; DS-UI-FRAME). Promoted from the Dashboard
 *  story so every page consumes one banner language. Renders a semantic
 *  status/alert region pairing a tone accent, a tinted surface, and a visible
 *  label — color is never the only channel. Loading shows the shipped spinner
 *  indicator. Class names (`dashboard-state*`) are preserved from the
 *  Dashboard proving ground so the regression sentinel stays: Dashboard
 *  consumes this component and its proven look/tests stay green. */
export type StateTone = "info" | "warning" | "danger";
export type StateRole = "status" | "alert";

const STATE_TONES: Record<StateTone, { accent: string; background: string; border: string }> = {
  info: { accent: "var(--info)", background: "var(--surface)", border: "var(--border-strong)" },
  warning: { accent: "var(--warning)", background: "var(--warning-bg)", border: "var(--warning-border)" },
  danger: { accent: "var(--danger)", background: "var(--danger-bg)", border: "var(--danger-border)" },
};

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
      {spinner ? <span className="spinner__indicator dashboard-state__spinner" aria-hidden="true" /> : null}
      <div className="dashboard-state__body">
        <h2 className="dashboard-state__title" style={{ color: tokens.accent }}>{title}</h2>
        {detail ? <p className="dashboard-state__detail">{detail}</p> : null}
      </div>
    </section>
  );
}
