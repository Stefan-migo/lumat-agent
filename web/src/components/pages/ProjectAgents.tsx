import { useCallback } from "react";
import { listProjectAgents } from "../../api";
import { useAsyncData } from "../../hooks/useAsyncData";
import { Badge } from "../primitives/Badge";
import { Button } from "../primitives/Button";
import { Card } from "../primitives/Card";
import { EmptyState } from "../shared/EmptyState";
import { StateMessage } from "../shared/StateMessage";

export function ProjectAgents({ projectSlug }: { projectSlug: string }) {
  const load = useCallback(() => listProjectAgents(projectSlug), [projectSlug]);
  const result = useAsyncData(load);

  return <Card title="Agentes del proyecto">
    {result.state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando agentes" /> : null}
    {result.state === "error" ? <><StateMessage tone="danger" role="alert" title="No pudimos cargar los agentes del proyecto" /><Button variant="secondary" onClick={result.retry}>Reintentar</Button></> : null}
    {result.state === "denied" ? <StateMessage tone="danger" role="alert" title="No tienes permiso para ver los agentes de este proyecto." /> : null}
    {result.state === "ready" ? <>
      <ul>
        {result.data?.agents.map((agent) => <li key={agent.key}>
          <h3>{agent.name} {agent.read_only ? <Badge tone="neutral">Solo lectura</Badge> : null}</h3>
          <p>{agent.role}</p>
          <p>{agent.description}</p>
        </li>)}
      </ul>
      <section aria-label="Última ejecución">
        <h3>Última ejecución</h3>
        {result.data?.latest_run ? <p>
          Estado: {result.data.latest_run.status}
          {result.data.latest_run.tool ? ` · Herramienta: ${result.data.latest_run.tool}` : ""}
          {result.data.latest_run.at ? ` · ${new Date(result.data.latest_run.at).toLocaleString("es-CL")}` : ""}
        </p> : <EmptyState title="Sin ejecuciones registradas" />}
      </section>
    </> : null}
  </Card>;
}
