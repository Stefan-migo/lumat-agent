/** KPI stat card emitting the tokenized `.kpi` primitive. */
export interface StatCardProps {
  label: string;
  value: number;
  context?: string;
  accent?: string;
}

export function StatCard({ label, value, context, accent }: StatCardProps) {
  return (
    <div className="kpi stat-card" style={{ borderTop: accent ? `var(--space-1) solid ${accent}` : undefined }}>
      <p className="kpi__label stat-card__label">{label}</p>
      <p className="kpi__value stat-card__value" style={{ fontVariantNumeric: "var(--corp-value)" }}>{value}</p>
      {context ? <p className="stat-card__context">{context}</p> : null}
    </div>
  );
}
