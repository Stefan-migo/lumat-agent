export type StateTone = "info" | "warning" | "danger" | "success";
export type StateRole = "status" | "alert";

const STATE_TONES: Record<StateTone, { accent: string; tint: string }> = {
  info: { accent: "var(--info)", tint: "var(--info-tint)" },
  warning: { accent: "var(--warning)", tint: "var(--warning-tint)" },
  danger: { accent: "var(--danger)", tint: "var(--danger-tint)" },
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

  .dashboard-state__spinner { border-top-color: var(--info); }
  .dashboard-state__body { display: grid; gap: var(--space-1); min-width: 0; }
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
    .dashboard-state__spinner { animation: none; }
  }
`;

export interface StateMessageProps {
  tone: StateTone;
  role: StateRole;
  title: string;
  detail?: string;
  spinner?: boolean;
}

export function StateMessage({ tone, role, title, detail, spinner = false }: StateMessageProps) {
  const tokens = STATE_TONES[tone];
  return (
    <section role={role} className="dashboard-state" style={{ background: tokens.tint, borderLeftColor: tokens.accent }}>
      <style>{STATE_STYLES}</style>
      {spinner ? <span className="spinner__indicator dashboard-state__spinner" aria-hidden="true" /> : null}
      <div className="dashboard-state__body">
        <h2 className="dashboard-state__title" style={{ color: tokens.accent }}>{title}</h2>
        {detail ? <p className="dashboard-state__detail">{detail}</p> : null}
      </div>
    </section>
  );
}
