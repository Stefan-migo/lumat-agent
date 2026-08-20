/** KPI stat card emitting the tokenized `.kpi` primitive (design D6).
 *  Dashboard-local: the dashboard is the only consumer (helpers.test renders
 *  it in isolation). Optional semantic top rail + verified context line follow
 *  the design-system KPI order: label, value, then verified context or change. */
export interface StatCardProps {
  label: string;
  value: number;
  /** Verified context line rendered after the value (e.g. window note). */
  context?: string;
  /** Top rail accent as a CSS var, e.g. "var(--primary-800)". */
  accent?: string;
}

export function StatCard({ label, value, context, accent }: StatCardProps) {
  return (
    <div
      className="kpi stat-card"
      style={{ borderTop: accent ? `var(--space-1) solid ${accent}` : undefined }}
    >
      <p className="kpi__label stat-card__label">{label}</p>
      <p className="kpi__value stat-card__value">{value}</p>
      {context ? <p className="stat-card__context">{context}</p> : null}
    </div>
  );
}
