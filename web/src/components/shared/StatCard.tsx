import type { ReactNode } from "react";

/** KPI stat card emitting the tokenized `.kpi` primitive. */
export interface StatMetric {
  label: string;
  value: ReactNode;
  context?: string;
}

interface SingleStatCardProps {
  label: string;
  value: number;
  context?: string;
  accent?: string;
}

interface MetricRowProps {
  metrics: [StatMetric, StatMetric, StatMetric];
  label?: never;
  value?: never;
  context?: never;
  accent?: never;
}

export type StatCardProps = SingleStatCardProps | MetricRowProps;

export function StatCard(props: StatCardProps) {
  if ("metrics" in props) {
    return (
      <div className="kpi stat-card stat-card--row">
        {props.metrics.map((metric) => (
          <div className="stat-card__metric" key={metric.label}>
            <p className="kpi__label stat-card__label">{metric.label}</p>
            <p className="kpi__value stat-card__value">{metric.value}</p>
            {metric.context ? <p className="stat-card__context">{metric.context}</p> : null}
          </div>
        ))}
      </div>
    );
  }

  const { label, value, context, accent } = props;
  return (
    <div className="kpi stat-card" style={{ borderTop: accent ? `var(--space-1) solid ${accent}` : undefined }}>
      <p className="kpi__label stat-card__label">{label}</p>
      <p className="kpi__value stat-card__value" style={{ fontVariantNumeric: "var(--corp-value)" }}>{value}</p>
      {context ? <p className="stat-card__context">{context}</p> : null}
    </div>
  );
}
