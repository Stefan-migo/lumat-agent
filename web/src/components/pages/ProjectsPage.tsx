import { useCallback, type ReactNode } from "react";
import { getProject, listProjects } from "../../api";
import type { ProjectDetailResponse, ProjectsResponse } from "../../types";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import { Button } from "../primitives/Button";
import { EmptyState } from "../shared/EmptyState";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";

export function ProjectsPage({ projectSlug, onOpenProject, data, state, sectionTabs }: { projectSlug?: string; onOpenProject?: (slug: string) => void; data?: ProjectsResponse; state?: AsyncDataState; sectionTabs?: ReactNode }) {
  const load = useCallback(() => listProjects(), []);
  const fetched = useAsyncData(load, data === undefined);
  const detailLoad = useCallback(() => getProject(projectSlug!), [projectSlug]);
  const detail = useAsyncData(detailLoad, projectSlug !== undefined);
  if (projectSlug) {
    const body = detail.data as ProjectDetailResponse | null;
    return <PageFrame title={body?.project.name ?? "Proyecto"} meta={body ? <span>{body.project.purpose}</span> : undefined} state={detail.state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando proyecto" /> : detail.state === "error" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar el proyecto" /> : undefined}>
      {sectionTabs}
      <Button variant="secondary" onClick={() => window.history.back()}>Volver a proyectos</Button>
      {body && Object.keys(body.artifacts).length === 0 ? <EmptyState title="No hay artefactos SDB" description="Este proyecto todavía no tiene artefactos de asistente." /> : <div className="ai-agent-grammar__thread-area" aria-label="Artefactos SDB">{body ? Object.entries(body.artifacts).map(([entity, artifacts]) => <section key={entity} aria-labelledby={`entity-${entity}`}><h2 id={`entity-${entity}`}>{entity}</h2><div className="ai-agent-grammar__bubbles">{artifacts.map((artifact) => <article className="ai-agent-grammar__bubble" key={artifact.id}><strong>{artifact.titulo}</strong><p>{artifact.contenido}</p><small>{artifact.tipo} · {artifact.topic_key}</small></article>)}</div></section>) : null}</div>}
    </PageFrame>;
  }
  const projects = data ?? fetched.data;
  const currentState = state ?? (data ? "ready" : fetched.state);
  return <PageFrame title="Proyectos" meta={<span>Browse de artefactos SDB</span>} state={currentState === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando proyectos" /> : currentState === "error" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar los proyectos" /> : undefined}>
    {sectionTabs}
    {!projects || projects.projects.length === 0 ? <EmptyState title="No hay proyectos" description="No hay namespaces registrados para mostrar." /> : <div className="ai-agent-grammar__thread-area" aria-label="Lista de proyectos"><div className="ai-agent-grammar__bubbles">{projects.projects.map((project) => <button type="button" className="ai-agent-grammar__bubble" key={project.slug} onClick={() => onOpenProject?.(project.slug)}><strong>{project.name}</strong><span>{project.purpose}</span><small>{project.status}</small></button>)}</div></div>}
  </PageFrame>;
}
