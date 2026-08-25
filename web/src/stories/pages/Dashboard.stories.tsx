import type { Meta, StoryObj } from "@storybook/react";
import { StateMessage } from "./_shared/StateMessage";
import { Avatar } from "../../components/primitives/Avatar";
import { activity, kpis } from "./_shared/mockData/dashboard";
import "../../components/primitives/primitives.css";

export type DashboardState = "ready" | "loading" | "empty" | "stale" | "partial-error" | "fatal-error";

interface DashboardOverviewProps {
  state?: DashboardState;
}

/** Dashboard-local styles (PANEL_SHELL_STYLES pattern): token-only, scoped
 *  under `.dashboard-shell` so shared primitives keep their defaults. The
 *  hero replaces the old titlebar (lime rail + forest tint); the activity
 *  card replaces the Motivos distribution table for the v1 friendly layout. */
const DASHBOARD_STYLES = `
  .dashboard-shell {
    display: grid;
    gap: var(--space-6);
    max-width: calc(var(--space-8) * 38);
    margin: 0 auto;
    font-family: var(--font-sans);
  }

  /* Hero — greeting + subtitle as a plain stacked heading block (the v1
   * "Nueva prueba" CTA was dropped; no flex layout needed anymore). */
  .dashboard-shell .dashboard-hero {
    display: grid;
    gap: var(--space-1);
  }

  .dashboard-shell .dashboard-hero__title {
    margin: 0;
    font-size: var(--text-3xl);
    font-weight: var(--weight-bold);
    line-height: var(--leading-tight);
    color: var(--text);
  }

  .dashboard-shell .dashboard-hero__subtitle {
    margin: var(--space-1) 0 0;
    font-size: var(--text-sm);
    color: var(--text-muted);
  }

  /* KPI delta — positive trend. Lower-is-better (e.g. response time down)
   * still renders with the success tone because direction is what matters. */
  .dashboard-shell .kpi__delta--positive {
    color: var(--success);
    font-weight: var(--weight-semibold);
  }

  /* Activity recent card. */
  .dashboard-shell .dashboard-activity {
    display: grid;
    gap: var(--space-3);
    padding: var(--space-4);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--surface);
  }

  .dashboard-shell .dashboard-activity__title {
    margin: 0;
    font-size: var(--text-lg);
    font-weight: var(--weight-bold);
    color: var(--text);
  }

  .dashboard-shell .dashboard-activity__list {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    gap: var(--space-3);
  }

  .dashboard-shell .dashboard-activity__row {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding-block: var(--space-2);
    border-top: 1px solid var(--border);
  }

  .dashboard-shell .dashboard-activity__row:first-child {
    border-top: 0;
    padding-top: 0;
  }

  /* Round the avatar in the activity row — the primitive ships as a rounded
   * square; the reference image uses circles. Local override keeps the
   * Avatar primitive's defaults untouched for other consumers. */
  .dashboard-shell .dashboard-activity__avatar {
    border-radius: 50%;
  }

  .dashboard-shell .dashboard-activity__body {
    display: grid;
    gap: var(--space-1);
    flex: 1;
    min-width: 0;
  }

  .dashboard-shell .dashboard-activity__name {
    margin: 0;
    font-size: var(--text-md);
    font-weight: var(--weight-semibold);
    color: var(--text);
  }

  .dashboard-shell .dashboard-activity__context {
    margin: 0;
    font-size: var(--text-sm);
    color: var(--text-muted);
  }

  .dashboard-shell .dashboard-activity__time {
    margin-left: auto;
    font-size: var(--text-sm);
    color: var(--text-muted);
    font-variant-numeric: var(--corp-value);
    white-space: nowrap;
  }
`;

export function DashboardOverview({ state = "ready" }: DashboardOverviewProps) {
  return (
    <main className="dashboard-shell">
      <style>{DASHBOARD_STYLES}</style>

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
          detail="Reintenta para recuperar los indicadores y la actividad reciente."
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
              detail="Los indicadores y la actividad reciente están vigentes, pero no pudimos actualizar el detalle. Reintenta en unos minutos."
            />
          ) : null}

          <section className="dashboard-hero" aria-label="Encabezado del panel">
            <h1 className="dashboard-hero__title">Buen día, equipo Lumat</h1>
            <p className="dashboard-hero__subtitle">Actividad del agente en los últimos 7 días</p>
          </section>

          <section aria-label="Indicadores principales">
            <div className="kpi-grid">
              {kpis.map((kpi) => (
                <div className="kpi" key={kpi.label}>
                  <p className="kpi__label">{kpi.label}</p>
                  <p className="kpi__value">{kpi.value}</p>
                  <p className={`kpi__delta kpi__delta--${kpi.deltaTone}`}>{kpi.delta}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="dashboard-activity" aria-label="Actividad reciente">
            <h2 className="dashboard-activity__title">Actividad reciente</h2>
            <ul className="dashboard-activity__list">
              {activity.map((row) => (
                <li key={row.id} className="dashboard-activity__row">
                  <Avatar name={row.name} className="dashboard-activity__avatar" />
                  <div className="dashboard-activity__body">
                    <p className="dashboard-activity__name">{row.title}</p>
                    <p className="dashboard-activity__context">{row.context}</p>
                  </div>
                  <time className="dashboard-activity__time">{row.time}</time>
                </li>
              ))}
            </ul>
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
          "Panel operativo de Lumat: saludo contextual, indicadores clave y actividad reciente del agente.\n\n" +
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
