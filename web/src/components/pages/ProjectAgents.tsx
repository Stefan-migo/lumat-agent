import { useCallback } from "react";
import { Bot, Compass, ShieldCheck, type LucideIcon } from "lucide-react";
import { listProjectAgents } from "../../api";
import { useAsyncData } from "../../hooks/useAsyncData";
import { Badge, type BadgeTone } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { Icon } from "../primitives/Icon";
import { EmptyState } from "../shared/EmptyState";
import { StateMessage } from "../shared/StateMessage";

// The three project roles are fixed system roles; the tile icon is a UI affordance, not data.
const AGENT_ICONS: Record<string, LucideIcon> = {
  orchestrator: Bot,
  verifier: ShieldCheck,
  explorer: Compass,
};

// The latest run is a recorded status, never a live feed: label it as a state, not as activity.
const RUN_STATUS: Record<string, { label: string; tone: BadgeTone }> = {
  completed: { label: "Completada", tone: "success" },
  planned: { label: "Planificada", tone: "neutral" },
  executing: { label: "En curso", tone: "neutral" },
  responding: { label: "En curso", tone: "neutral" },
  running: { label: "En curso", tone: "neutral" },
  approval_pending: { label: "Pendiente de aprobación", tone: "warning" },
  degraded: { label: "Degradada", tone: "warning" },
  failed: { label: "Fallida", tone: "danger" },
  error: { label: "Fallida", tone: "danger" },
};

export function ProjectAgents({ projectSlug }: { projectSlug: string }) {
  const load = useCallback(() => listProjectAgents(projectSlug), [projectSlug]);
  const result = useAsyncData(load);
  const run = result.data?.latest_run ?? null;
  const runStatus = run ? (RUN_STATUS[run.status] ?? { label: run.status, tone: "neutral" as BadgeTone }) : null;

  return <div className="project-agents">
    <Card title="Agentes del proyecto" description="Roles disponibles para trabajar con el contexto del proyecto.">
      {result.state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando agentes" /> : null}
      {result.state === "error" ? <><StateMessage tone="danger" role="alert" title="No pudimos cargar los agentes del proyecto" /><Button variant="secondary" onClick={result.retry}>Reintentar</Button></> : null}
      {result.state === "denied" ? <StateMessage tone="danger" role="alert" title="No tienes permiso para ver los agentes de este proyecto." /> : null}
      {result.state === "ready" ? <ul className="project-agents__list">
        {result.data?.agents.map((agent) => <li className="project-agents__card" key={agent.key}>
          <span className="project-agents__icon" aria-hidden="true"><Icon icon={AGENT_ICONS[agent.key] ?? Bot} /></span>
          <div className="project-agents__copy">
            <div className="project-agents__heading">
              <h3>{agent.name}</h3>
              <Badge tone="neutral">{agent.role}</Badge>
            </div>
            <p>{agent.description}</p>
          </div>
        </li>)}
      </ul> : null}
    </Card>
    <Card title="Última ejecución" description="Estado registrado de la ejecución más reciente.">
      {result.state === "ready" ? (run && runStatus ? <div className="project-agents__run">
        <Badge tone={runStatus.tone}>{runStatus.label}</Badge>
        {run.tool ? <span className="project-agents__run-detail">Herramienta: {run.tool}</span> : null}
        {run.at ? <time className="project-agents__run-detail" dateTime={run.at}>{new Date(run.at).toLocaleString("es-CL")}</time> : null}
      </div> : <EmptyState title="Sin ejecuciones registradas" />) : null}
    </Card>
  </div>;
}
