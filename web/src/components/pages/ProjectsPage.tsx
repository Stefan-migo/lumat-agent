import { useCallback, type ReactNode } from "react";
import { getProject, listProjects } from "../../api";
import type { ProjectDetailResponse, ProjectsResponse } from "../../types";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import { Button } from "../primitives/Button";
import { Badge } from "../primitives/Badge";
import { EmptyState } from "../shared/EmptyState";
import { DataTable } from "../shared/DataTable";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { memoryStatusLabel, memoryStatusTone, memoryTypeLabel, memoryTypeTone, projectStatusLabel, projectStatusTone } from "../shared/toneMaps";

export function ProjectsPage({ projectSlug, onOpenProject, data, state, sectionTabs }: { projectSlug?: string; onOpenProject?: (slug: string) => void; data?: ProjectsResponse; state?: AsyncDataState; sectionTabs?: ReactNode }) {
  const load = useCallback(() => listProjects(), []);
  const fetched = useAsyncData(load, data === undefined);
  const detailLoad = useCallback(() => getProject(projectSlug!), [projectSlug]);
  const detail = useAsyncData(detailLoad, projectSlug !== undefined);
  if (projectSlug) {
    const body = detail.data as ProjectDetailResponse | null;
    return <PageFrame title={body?.project.name ?? "Proyecto"} meta={body ? <span>{body.project.purpose} · <Badge tone={projectStatusTone(body.project.status)}>{projectStatusLabel(body.project.status)}</Badge></span> : undefined} actions={<Button variant="secondary" onClick={() => window.history.back()}>Volver a proyectos</Button>} state={detail.state === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando proyecto" /> : detail.state === "error" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar el proyecto" /> : undefined}>
      {sectionTabs}
      {body && Object.keys(body.artifacts).length === 0 ? <EmptyState title="No hay artefactos SDB" description="Este proyecto todavía no tiene artefactos de asistente." /> : body ? Object.entries(body.artifacts).map(([entity, artifacts]) => <section aria-labelledby={`entity-${entity}`} key={entity}><h2 id={`entity-${entity}`}>{entity}</h2><DataTable rows={artifacts} rowKey={(artifact) => String(artifact.id)} emptyMessage="No hay artefactos para esta entidad" columns={[{ key: "title", header: "Título", render: (artifact) => artifact.titulo }, { key: "content", header: "Contenido", render: (artifact) => artifact.contenido }, { key: "type", header: "Tipo", render: (artifact) => <Badge tone={memoryTypeTone(artifact.tipo)}>{memoryTypeLabel(artifact.tipo)}</Badge> }, { key: "status", header: "Estado", render: (artifact) => <Badge tone={memoryStatusTone(artifact.status)}>{memoryStatusLabel(artifact.status)}</Badge> }, { key: "topic", header: "Identificador técnico", render: (artifact) => <small>{artifact.topic_key}</small> }]} /></section>) : null}
    </PageFrame>;
  }
  const projects = data ?? fetched.data;
  const currentState = state ?? (data ? "ready" : fetched.state);
  return <PageFrame title="Proyectos" meta={<span>Explora los artefactos SDB</span>} state={currentState === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando proyectos" /> : currentState === "error" ? <StateMessage tone="danger" role="alert" title="No pudimos cargar los proyectos" /> : undefined}>
    {sectionTabs}
    {!projects || projects.projects.length === 0 ? <EmptyState title="No hay proyectos" description="No hay espacios de proyecto registrados para mostrar." /> : <DataTable rows={projects.projects} rowKey={(project) => project.slug} columns={[{ key: "name", header: "Proyecto", render: (project) => <Button variant="tertiary" onClick={() => onOpenProject?.(project.slug)}>{project.name}</Button> }, { key: "purpose", header: "Propósito", render: (project) => project.purpose }, { key: "status", header: "Estado", render: (project) => <Badge tone={projectStatusTone(project.status)}>{projectStatusLabel(project.status)}</Badge> }]} />}
  </PageFrame>;
}
