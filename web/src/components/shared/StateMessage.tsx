export type StateTone = "info" | "warning" | "danger" | "success";
export type StateRole = "status" | "alert";

const STATE_TONES: Record<StateTone, { accent: string; tint: string }> = {
  info: { accent: "var(--info)", tint: "var(--info-tint)" },
  warning: { accent: "var(--warning)", tint: "var(--warning-tint)" },
  danger: { accent: "var(--danger)", tint: "var(--danger-tint)" },
  success: { accent: "var(--success)", tint: "var(--success-tint)" },
};

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
      {spinner ? <span className="spinner__indicator dashboard-state__spinner" aria-hidden="true" /> : null}
      <div className="dashboard-state__body">
        <h2 className="dashboard-state__title" style={{ color: tokens.accent }}>{title}</h2>
        {detail ? <p className="dashboard-state__detail">{detail}</p> : null}
      </div>
    </section>
  );
}
