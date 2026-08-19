/** KPI stat card emitting the tokenized `.kpi` primitive (design D6). */
export interface StatCardProps {
  label: string;
  value: number;
}

export function StatCard({ label, value }: StatCardProps) {
  return (
    <div className="kpi">
      <p className="kpi__label">{label}</p>
      <p className="kpi__value">{value}</p>
    </div>
  );
}
