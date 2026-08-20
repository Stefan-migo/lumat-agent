import type { Meta, StoryObj } from "@storybook/react";
import type { Column } from "./_shared/DataTable";
import { DataTable } from "./_shared/DataTable";
import { StatCard } from "./_shared/StatCard";
import { PageHeader } from "./_shared/PageHeader";
import { StateMessage } from "./_shared/StateMessage";
import { kpis } from "./_shared/mockData/dashboard";
import "../../components/primitives/primitives.css";

export type DashboardState = "ready" | "loading" | "empty" | "stale" | "partial-error" | "fatal-error";

interface DashboardOverviewProps {
  state?: DashboardState;
}

/** Dashboard-local styles (PANEL_SHELL_STYLES pattern): token-only, scoped
 *  under `.dashboard-shell` so shared primitives keep their defaults. */
const DASHBOARD_STYLES = `
  .dashboard-shell {
    display: grid;
    gap: var(--space-5);
    max-width: calc(var(--space-8) * 38);
    margin: 0 auto;
    font-family: var(--font-sans);
  }

  /* Title region — echoes the shell brand block: lime leading rail over a
     soft forest tint (same language as the active navigation item). */
  .dashboard-shell__titlebar {
    padding: var(--space-4) var(--space-4) 0;
    border: 1px solid var(--border);
    border-left: var(--space-1) solid var(--brand-lime);
    border-radius: var(--radius-md);
    background: var(--primary-100);
  }

  /* KPI grid — auto-fit keeps 1..3 columns down to narrow widths. */
  .dashboard-shell .kpi-grid {
    grid-template-columns: repeat(auto-fit, minmax(min(100%, calc(var(--space-8) * 7)), 1fr));
  }

  .dashboard-shell .stat-card {
    gap: var(--space-2);
  }

  .dashboard-shell .stat-card__label {
    font-weight: var(--weight-semibold);
    letter-spacing: 0.01em;
  }

  .dashboard-shell .stat-card__value {
    font-weight: var(--weight-bold);
    font-variant-numeric: tabular-nums;
    line-height: var(--leading-tight);
  }

  .dashboard-shell .stat-card__context {
    margin: 0;
    padding-top: var(--space-2);
    border-top: 1px solid var(--border);
    color: var(--text-muted);
    font-size: var(--text-xs);
    line-height: var(--leading-snug);
  }

  /* Section card (Motivos) */
  .dashboard-shell .dashboard-section {
    display: grid;
    gap: var(--space-3);
    padding: var(--space-4);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--surface);
  }

  .dashboard-shell .dashboard-section__eyebrow {
    margin: 0;
    color: var(--info);
    font-size: var(--text-sm);
    font-weight: var(--weight-semibold);
  }

  .dashboard-shell .dashboard-section__title {
    margin: 0;
    color: var(--text);
    font-size: var(--text-lg);
  }

  .dashboard-shell .dashboard-section__scroll {
    overflow-x: auto;
  }

  /* Motivos table refinements: tabular comparable counts, bar track/fill. */
  .dashboard-shell .dashboard-table__count {
    font-weight: var(--weight-semibold);
    font-variant-numeric: tabular-nums;
  }

  .dashboard-shell .dashboard-motivos__cell {
    display: grid;
    gap: var(--space-2);
    min-width: calc(var(--space-8) * 6);
  }

  .dashboard-shell .dashboard-motivos__track {
    display: block;
    height: var(--space-2);
    overflow: hidden;
    border-radius: var(--radius-sm);
    background: var(--table-head-bg);
  }

  .dashboard-shell .dashboard-motivos__fill {
    display: block;
    height: 100%;
    border-radius: var(--radius-sm);
    background: var(--brand-cyan);
  }

  /* State surfaces — semantic pairs, colored rail + explicit label (never
     color alone). Loading uses the shipped spinner indicator. */
  .dashboard-shell .dashboard-state {
    display: flex;
    gap: var(--space-3);
    align-items: flex-start;
    padding: var(--space-4);
    border: 1px solid;
    border-left-width: var(--space-1);
    border-radius: var(--radius-md);
  }

  .dashboard-shell .dashboard-state__spinner {
    margin-top: var(--space-1);
    border-top-color: var(--info);
  }

  .dashboard-shell .dashboard-state__body {
    display: grid;
    gap: var(--space-1);
  }

  .dashboard-shell .dashboard-state__title {
    margin: 0;
    font-size: var(--text-lg);
    font-weight: var(--weight-bold);
    line-height: var(--leading-tight);
  }

  .dashboard-shell .dashboard-state__detail {
    margin: 0;
    color: var(--text-muted);
    font-size: var(--text-sm);
    line-height: var(--leading-normal);
  }

  @media (prefers-reduced-motion: reduce) {
    .dashboard-shell .dashboard-state__spinner {
      animation: none;
    }
  }
`;

function formatWindowStart(value: string) {
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(
    new Date(`${value}T00:00:00Z`),
  );
}

/** Dashboard body (3 KPI cards + Motivos table + window caption).
 *  Exported so tests can render it directly; hidden from the addons panel. */
export function DashboardOverview({ state = "ready" }: DashboardOverviewProps) {
  const motivosColumns: Column<[string, number]>[] = [
    { key: "service", header: "Motivo", render: ([service]) => service },
    {
      key: "count",
      header: "Cantidad",
      align: "right",
      render: ([, count]) => <span className="dashboard-table__count">{count}</span>,
    },
  ];

  const maximum = Math.max(...kpis.motivos.map(([, count]) => count));
  const caption = `Ventana de ${kpis.window_days} días · desde ${formatWindowStart(kpis.window_start)}`;
  const windowNote = `Ventana de ${kpis.window_days} días`;

  return (
    <main className="dashboard-shell">
      <style>{DASHBOARD_STYLES}</style>

      <div className="dashboard-shell__titlebar">
        <PageHeader title="Panel" meta={caption} />
      </div>

      {state === "loading" ? (
        <StateMessage
          tone="info"
          role="status"
          spinner
          title="Cargando indicadores"
          detail="Estamos reuniendo la actividad reciente de la operación."
        />
      ) : state === "fatal-error" ? (
        <StateMessage
          tone="danger"
          role="alert"
          title="No pudimos cargar el panel"
          detail="Reintenta para recuperar los indicadores y el detalle de motivos."
        />
      ) : state === "empty" ? (
        <StateMessage
          tone="info"
          role="status"
          title="Aún no hay actividad en esta ventana"
          detail="Cuando ingresen contactos, aquí verás derivaciones, solicitudes de visita y motivos de atención."
        />
      ) : (
        <>
          {state === "stale" ? (
            <StateMessage
              tone="warning"
              role="status"
              title="Datos posiblemente desactualizados"
              detail="La última consulta no pudo completarse. Mostramos la información disponible para mantener el contexto operativo."
            />
          ) : state === "partial-error" ? (
            <StateMessage
              tone="danger"
              role="status"
              title="Una parte del panel no está disponible"
              detail="Los indicadores están vigentes, pero no pudimos actualizar el detalle de motivos. Reintenta en unos minutos."
            />
          ) : null}

          <section aria-label="Indicadores principales">
            <div className="kpi-grid">
              <StatCard
                label="Contactos"
                value={kpis.contacts}
                accent="var(--primary-800)"
                context={windowNote}
              />
              <StatCard
                label="Derivados"
                value={kpis.derived}
                accent="var(--warning)"
                context={windowNote}
              />
              <StatCard
                label="Solicitudes de visita"
                value={kpis.visit_requests}
                accent="var(--brand-cyan)"
                context={windowNote}
              />
            </div>
          </section>

          <section aria-labelledby="motivos-title" className="dashboard-section">
            <div>
              <p className="dashboard-section__eyebrow">Distribución de demanda</p>
              <h2 id="motivos-title" className="dashboard-section__title">Motivos</h2>
            </div>
            {state === "partial-error" ? (
              <StateMessage
                tone="danger"
                role="alert"
                title="Detalle no disponible"
                detail="Los totales superiores siguen visibles para conservar el contexto."
              />
            ) : (
              <div className="dashboard-section__scroll">
                <DataTable
                  columns={motivosColumns.map((column) =>
                    column.key === "service"
                      ? {
                          ...column,
                          render: ([service, count]: [string, number]) => (
                            <div className="dashboard-motivos__cell">
                              <span>{service}</span>
                              <span className="dashboard-motivos__track" aria-hidden="true">
                                <span
                                  className="dashboard-motivos__fill"
                                  style={{ width: `${(count / maximum) * 100}%` }}
                                />
                              </span>
                            </div>
                          ),
                        }
                      : column,
                  )}
                  rows={kpis.motivos}
                  rowKey={([service]) => service}
                />
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}

const meta = {
  title: "pages/Dashboard",
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          'Panel operativo de Lumat: contactos, derivaciones, solicitudes de visita y distribución de motivos para una ventana explícita (R-PRD-PG-6).\n\n' +
          "**Uso** — inicio autenticado para escanear demanda y detectar excepciones.\n" +
          "**Estados** — listo, carga, vacío, datos obsoletos, error parcial y error fatal.\n" +
          "**Fuente** — mock page-first con la forma del serializer productivo; el wiring de producción no cambia.",
      },
    },
  },
  excludeStories: ["DashboardOverview"],
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Overview: Story = {
  render: () => <DashboardOverview />,
};

export const Loading: Story = { render: () => <DashboardOverview state="loading" /> };
export const Empty: Story = { render: () => <DashboardOverview state="empty" /> };
export const Stale: Story = { render: () => <DashboardOverview state="stale" /> };
export const PartialError: Story = { render: () => <DashboardOverview state="partial-error" /> };
export const FatalError: Story = { render: () => <DashboardOverview state="fatal-error" /> };
